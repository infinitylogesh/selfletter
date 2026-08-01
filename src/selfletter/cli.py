#!/usr/bin/env python3
"""
SelfLetter CLI - Fetches content from arXiv/blogs and summarizes via OpenAI.
"""

import os
import re
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from notion_client import Client as NotionClient

from .prompts import SUMMARY as SUMMARY_PROMPT
from .processors import ProcessorFactory
from .combiner import NewsletterCombiner
from .utils.notion import (
    get_page_title, get_url_property, get_retry_count,
    safe_set_error, increment_retry_count, mark_done
)
from .utils.email import send_email

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
def get_config():
    load_dotenv()
    return {
        "SOURCE_DB_ID": os.environ["NOTION_SOURCE_DB_ID"],
        "NOTION_TOKEN": os.environ["NOTION_TOKEN"],
        "API_KEY": os.environ["API_KEY"],
        "OUTPUT_DIR": os.environ.get("OUTPUT_DIR", "newsletter"),
        "MODEL": os.environ.get("MODEL", "gpt-4o-mini"),
        "ENDPOINT": os.environ.get("ENDPOINT", "https://openrouter.ai/api/v1"),
        "MAX_CHARS": int(os.environ.get("MAX_CHARS", "200000")),
        "USER_AGENT": os.environ.get("USER_AGENT", "NotionSummarizerBot/1.0"),
        "MAX_RETRIES": int(os.environ.get("MAX_RETRIES", "3")),
        "PROP_URL": os.environ.get("NOTION_PROP_URL", "URL"),
        "PROP_DONE": os.environ.get("NOTION_PROP_DONE", "Summarized"),
        "PROP_ERR": os.environ.get("NOTION_PROP_ERR", "Last error"),
        "PROP_RETRY": os.environ.get("NOTION_PROP_RETRY", "Retry count"),
    }

def sanitize_filename(name: str) -> str:
    """Convert title to safe filename."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name if name else "untitled"


def save_summary_to_file(output_dir: str, title: str, source_url: str, typ: str, summary: str, date_str: str = None):
    """Save summary to a markdown file in date-based folder structure."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    folder = Path(output_dir) / date_str / typ
    folder.mkdir(parents=True, exist_ok=True)

    safe_title = sanitize_filename(title or source_url)
    filename = f"{safe_title}.md"
    filepath = folder / filename

    counter = 1
    while filepath.exists():
        filename = f"{safe_title}-{counter}.md"
        filepath = folder / filename
        counter += 1

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


def is_url_already_processed(output_dir: str, url: str) -> bool:
    """Check if a URL has already been processed by looking at local files."""
    folder = Path(output_dir)
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


def query_unprocessed(notion: NotionClient, database_id: str, prop_done: str, date: str, page_size: int = 100) -> dict:
    """Query Notion for unprocessed pages."""
    return notion.databases.query(
        database_id=database_id,
        page_size=page_size,
        filter={
            "and": [
                {"property": prop_done, "checkbox": {"equals": False}},
                {"property": "Created", "date": {"equals": date}},
            ]
        },
    )


def process_one(notion: NotionClient, page: dict, processor_factory: ProcessorFactory, config: dict, date_str: str = None) -> bool:
    """Process a single Notion page."""
    page_id = page["id"]
    title = get_page_title(page)
    url = get_url_property(page, config["PROP_URL"])

    if not url:
        logger.warning(f"Page {page_id} missing URL property")
        safe_set_error(notion, page_id, config["PROP_ERR"], f"Missing URL property '{config['PROP_URL']}'.")
        return True

    retry_count = get_retry_count(page, config["PROP_RETRY"])
    if retry_count >= config["MAX_RETRIES"]:
        logger.warning(f"Page {page_id} exceeded max retries ({config['MAX_RETRIES']}), skipping")
        safe_set_error(notion, page_id, config["PROP_ERR"], f"Max retries ({config['MAX_RETRIES']}) exceeded")
        return True

    try:
        if is_url_already_processed(config["OUTPUT_DIR"], url):
            logger.info(f"URL already processed, skipping: {url}")
            return True

        processor = processor_factory.get_processor(url)
        final_title, content_type, actual_url, summary = processor.process(url, title)

        save_summary_to_file(
            config["OUTPUT_DIR"],
            title=final_title,
            source_url=actual_url,
            typ=content_type,
            summary=summary,
            date_str=date_str,
        )

        # mark_done(notion, page_id, config["PROP_DONE"], done=True)
        logger.info(f"Successfully processed: {final_title}")
        return True

    except Exception as e:
        logger.error(f"Error processing page {page_id}: {e}")
        safe_set_error(notion, page_id, config["PROP_ERR"], f"{type(e).__name__}: {str(e)[:500]}")
        increment_retry_count(notion, page_id, config["PROP_RETRY"], retry_count)
        time.sleep(1)
        return False


def main():
    """Main entry point."""
    config = get_config()
    logger.info("Starting SelfLetter Digest")
    start_time = datetime.now()

    notion = NotionClient(auth=config["NOTION_TOKEN"])
    
    processor_factory = ProcessorFactory(
        openai_api_key=config["API_KEY"],
        openai_model=config["MODEL"],
        openai_endpoint=config["ENDPOINT"],
        summary_prompt=SUMMARY_PROMPT,
        max_chars=config["MAX_CHARS"],
        user_agent=config["USER_AGENT"],
    )
    
    combiner = NewsletterCombiner(output_dir=config["OUTPUT_DIR"])

    try:
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_date = yesterday.strftime("%Y-%m-%d")
        
        resp = query_unprocessed(notion, config["SOURCE_DB_ID"], config["PROP_DONE"], yesterday_date)
        results = resp.get("results", [])

        if not results:
            logger.info(f"No unprocessed items found for {yesterday_date}")
            return

        logger.info(f"Processing {len(results)} items")

        success_count = 0
        for page in results:
            if process_one(notion, page, processor_factory, config, date_str=yesterday_date):
                success_count += 1

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Processed {success_count}/{len(results)} items in {elapsed:.1f}s")
        
        if success_count > 0:
            logger.info("Combining daily summaries into newsletter...")
            newsletter_path = combiner.combine_daily_summaries(yesterday_date)
            if newsletter_path:
                logger.info(f"Daily newsletter created: {newsletter_path}")
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

