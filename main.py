#!/usr/bin/env python3
"""
Notion Summarizer - Fetches content from arXiv/blogs and summarizes via OpenAI.
Designed to run as a daily cron job via GitHub Actions.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import re
import time
import logging
import smtplib
import markdown
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from email.message import EmailMessage

from notion_client import Client as NotionClient
from prompt import SUMMARY as SUMMARY_PROMPT
from processors import ProcessorFactory
from combiner import NewsletterCombiner
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ----------------------------
# Config (edit to match your DB property names)
# ----------------------------
SOURCE_DB_ID = os.environ["NOTION_SOURCE_DB_ID"]
DEST_DB_ID = os.environ.get("NOTION_DEST_DB_ID")  # Optional: kept for backward compat, used for dedup check

# Output directory for summaries (local file storage)
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "newsletter")

PROP_URL = os.environ.get("NOTION_PROP_URL", "URL")
PROP_DONE = os.environ.get("NOTION_PROP_DONE", "Summarized")
PROP_ERR = os.environ.get("NOTION_PROP_ERR", "Last error")  # optional
PROP_RETRY = os.environ.get("NOTION_PROP_RETRY", "Retry count")  # optional

DEST_PROP_TITLE = os.environ.get("NOTION_DEST_PROP_TITLE", "Name")
DEST_PROP_URL = os.environ.get("NOTION_DEST_PROP_URL", "Source URL")
DEST_PROP_TYPE = os.environ.get("NOTION_DEST_PROP_TYPE", "Type")
DEST_PROP_SUMM = os.environ.get("NOTION_DEST_PROP_SUMM", "Summary")
DEST_PROP_DATE = os.environ.get("NOTION_DEST_PROP_DATE", "Added")

NOTION_TOKEN = os.environ["NOTION_TOKEN"]

OPENAI_API_KEY = os.environ["API_KEY"]
OPENAI_MODEL = os.environ.get("MODEL", "gpt-4o-mini")
OPENAI_ENDPOINT = os.environ.get("ENDPOINT", "https://openrouter.ai/api/v1")

# Safety limits to keep cost bounded
MAX_CHARS = int(os.environ.get("MAX_CHARS", "120000"))

# User agent for HTTP requests
UA = os.environ.get("USER_AGENT", "NotionSummarizerBot/1.0 (+https://github.com/yourusername/selfletter)")

# Retry configuration
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))





def notion_rich_text(s: str, chunk: int = 1800) -> list:
    """Split text into Notion rich text blocks."""
    s = s or ""
    parts = [s[i : i + chunk] for i in range(0, len(s), chunk)]
    if not parts:
        return [{"type": "text", "text": {"content": ""}}]
    return [{"type": "text", "text": {"content": p}} for p in parts]


def get_page_title(page: dict) -> str:
    """Extract title from a Notion page."""
    props = page.get("properties", {})
    for k, v in props.items():
        if v.get("type") == "title":
            title_arr = v.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_arr).strip()
    return ""


def get_url_property(page: dict) -> Optional[str]:
    """Extract URL from a Notion page property."""
    props = page.get("properties", {})
    p = props.get(PROP_URL)
    if not p:
        return None
    if p.get("type") == "url":
        return p.get("url")
    return None


def get_retry_count(page: dict) -> int:
    """Get current retry count from page."""
    props = page.get("properties", {})
    p = props.get(PROP_RETRY)
    if p and p.get("type") == "number":
        return p.get("number") or 0
    return 0


def safe_set_error(notion: NotionClient, page_id: str, msg: str):
    """Safely set error message on a Notion page."""
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                PROP_ERR: {"rich_text": notion_rich_text(msg[:4000])},
            },
        )
    except Exception as e:
        err_msg = str(e)
        if "does not exist" in err_msg:
            logger.warning(f"Error property '{PROP_ERR}' not found in Notion database. Skipping error logging to Notion.")
        else:
            logger.error(f"Failed to set error on page {page_id}: {e}")


def increment_retry_count(notion: NotionClient, page_id: str, current_count: int):
    """Increment retry count on a Notion page."""
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                PROP_RETRY: {"number": current_count + 1},
            },
        )
    except Exception as e:
        err_msg = str(e)
        if "does not exist" in err_msg:
            logger.warning(f"Retry count property '{PROP_RETRY}' not found in Notion database. Skipping.")
        else:
            logger.warning(f"Failed to increment retry count: {e}")


def mark_done(notion: NotionClient, page_id: str, done: bool = True):
    """Mark a page as processed."""
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                PROP_DONE: {"checkbox": bool(done)}
            },
        )
    except Exception as e:
        logger.error(f"Failed to mark page {page_id} as done: {e}")


def sanitize_filename(name: str) -> str:
    """Convert title to safe filename."""
    # Lowercase, replace spaces with dashes, remove special chars
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name if name else "untitled"


def save_summary_to_file(
    title: str,
    source_url: str,
    typ: str,
    summary: str,
    date_str: str = None,
):
    """Save summary to a markdown file in date-based folder structure."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # Create folder: newsletter/YYYY-MM-DD/{type}/
    folder = Path(OUTPUT_DIR) / date_str / typ
    folder.mkdir(parents=True, exist_ok=True)

    # Generate filename from title
    safe_title = sanitize_filename(title or source_url)
    filename = f"{safe_title}.md"
    filepath = folder / filename

    # Handle duplicate filenames
    counter = 1
    while filepath.exists():
        filename = f"{safe_title}-{counter}.md"
        filepath = folder / filename
        counter += 1

    # Create markdown content with frontmatter
    now = datetime.now(timezone.utc).isoformat()
    content = f"""---
title: "{title or source_url}"
source_url: "{source_url}"
type: "{typ}"
date: "{now}"
---

{summary}
"""

    filepath.write_text(content)
    logger.info(f"Saved summary to: {filepath}")


def is_url_already_processed(url: str) -> bool:
    """Check if a URL has already been processed by looking at local files."""
    folder = Path(OUTPUT_DIR)
    if not folder.exists():
        return False

    for md_file in folder.rglob("*.md"):
        try:
            content = md_file.read_text()
            if url in content:
                return True
        except Exception:
            continue
    return False


def query_unprocessed(notion: NotionClient, date: str, page_size: int = 100) -> dict:
    """Query Notion for unprocessed pages (filter by date in Python)."""
    return notion.databases.query(
        database_id=SOURCE_DB_ID,
        page_size=page_size,
        filter={
            "and": [
                {"property": PROP_DONE, "checkbox": {"equals": False}},
                {"property": "Created", "date": {"equals": date}},
            ]
        },
    )


def process_one(notion: NotionClient, page: dict, processor_factory: ProcessorFactory, date_str: str = None) -> bool:
    """Process a single Notion page using the processor factory."""
    page_id = page["id"]
    title = get_page_title(page)
    url = get_url_property(page)

    if not url:
        logger.warning(f"Page {page_id} missing URL property")
        safe_set_error(notion, page_id, f"Missing URL property '{PROP_URL}'.")
        # mark_done(notion, page_id, done=True)
        return True  # Skip this page, no URL to process

    retry_count = get_retry_count(page)
    if retry_count >= MAX_RETRIES:
        logger.warning(f"Page {page_id} exceeded max retries ({MAX_RETRIES}), skipping")
        safe_set_error(notion, page_id, f"Max retries ({MAX_RETRIES}) exceeded")
        # mark_done(notion, page_id, done=True)
        return True

    try:
        # Check if already processed
        if is_url_already_processed(url):
            logger.info(f"URL already processed, skipping: {url}")
            # mark_done(notion, page_id, done=True)
            return True

        # Get appropriate processor for this URL
        processor = processor_factory.get_processor(url)
        
        # Process the content
        final_title, content_type, actual_url, summary = processor.process(url, title)

        # Save summary to file
        save_summary_to_file(
            title=final_title,
            source_url=actual_url,
            typ=content_type,
            summary=summary,
            date_str=date_str,
        )

        # mark_done(notion, page_id, done=True)
        logger.info(f"Successfully processed: {final_title}")
        return True

    except Exception as e:
        logger.error(f"Error processing page {page_id}: {e}")
        safe_set_error(notion, page_id, f"{type(e).__name__}: {str(e)[:500]}")
        increment_retry_count(notion, page_id, retry_count)
        time.sleep(1)
        return False


def send_email(subject: str, body_markdown: str):
    """Send summary via email using SMTP (rendered HTML)."""
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    email_to = os.environ.get("EMAIL_TO")
    email_from = os.environ.get("EMAIL_FROM", user)

    if not all([user, password, email_to]):
        logger.warning("Email configuration missing (SMTP_USER, SMTP_PASS, EMAIL_TO). Skipping email.")
        return

    # Convert Markdown to HTML
    html_content = markdown.markdown(body_markdown)
    
    # Add some basic styling for better email rendering
    styled_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #1a1a1a; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            h2 {{ color: #2c3e50; margin-top: 30px; border-bottom: 1px solid #eee; }}
            h3 {{ color: #34495e; margin-top: 20px; }}
            a {{ color: #3498db; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            code {{ background-color: #f8f8f8; padding: 2px 4px; border-radius: 4px; font-family: monospace; }}
            hr {{ border: 0; border-top: 1px solid #eee; margin: 30px 0; }}
            blockquote {{ border-left: 4px solid #eee; padding-left: 15px; color: #666; font-style: italic; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to
    
    # Set the plain text version as a fallback
    msg.set_content(body_markdown)
    
    # Add the HTML version
    msg.add_alternative(styled_html, subtype="html")

    try:
        # SSL on 465 (simple + reliable)
        with smtplib.SMTP_SSL(host, port) as server:
            server.login(user, password)
            server.send_message(msg)
        logger.info(f"Email sent successfully to {email_to}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


def main():
    """Main entry point."""
    logger.info("Starting Notion Summarizer")
    start_time = datetime.now()

    notion = NotionClient(auth=NOTION_TOKEN)
    
    # Initialize processor factory
    processor_factory = ProcessorFactory(
        openai_api_key=OPENAI_API_KEY,
        openai_model=OPENAI_MODEL,
        openai_endpoint=OPENAI_ENDPOINT,
        summary_prompt=SUMMARY_PROMPT,
        max_chars=MAX_CHARS,
        user_agent=UA,
    )
    
    # Initialize newsletter combiner
    combiner = NewsletterCombiner(output_dir=OUTPUT_DIR)

    try:
        # Default to yesterday's date
        from datetime import timedelta
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_date = yesterday.strftime("%Y-%m-%d")
        
        resp = query_unprocessed(notion, yesterday_date, page_size=100)
        results = resp.get("results", [])

        if not results:
            logger.info("No unprocessed items found")
            print(f"[{datetime.now(timezone.utc).isoformat()}] No items to process (Read=false).")
            return

        logger.info(f"Processing {len(results)} items")

        success_count = 0
        for page in results:
            if process_one(notion, page, processor_factory, date_str=yesterday_date):
                success_count += 1

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Processed {success_count}/{len(results)} items in {elapsed:.1f}s")
        print(f"[{datetime.now(timezone.utc).isoformat()}] Processed {success_count}/{len(results)} items in {elapsed:.1f}s")
        
        # Combine daily summaries into newsletter
        if success_count > 0:
            logger.info("Combining daily summaries into newsletter...")
            newsletter_path = combiner.combine_daily_summaries(yesterday_date)
            if newsletter_path:
                logger.info(f"Daily newsletter created: {newsletter_path}")
                print(f"[{datetime.now(timezone.utc).isoformat()}] Daily newsletter created: {newsletter_path}")
                
                # Send newsletter via email
                content = Path(newsletter_path).read_text()
                send_email(
                    subject=f"Daily AI Digest - {yesterday_date}",
                    body_markdown=content
                )

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
