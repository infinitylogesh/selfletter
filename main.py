#!/usr/bin/env python3
"""
Notion Summarizer - Fetches content from arXiv/blogs and summarizes via OpenAI.
Designed to run as a daily cron job via GitHub Actions.
"""

import os
import re
import time
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from notion_client import Client as NotionClient
import trafilatura
from bs4 import BeautifulSoup

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
DEST_DB_ID = os.environ["NOTION_DEST_DB_ID"]

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

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_ENDPOINT = os.environ.get("OPENAI_ENDPOINT", "https://api.openai.com/v1/responses")

# Your custom summarization prompt template.
# Use {title}, {url}, {content} placeholders.
SUMMARY_PROMPT = os.environ.get(
    "SUMMARY_PROMPT",
    """Summarize the following content concisely.

Title: {title}
URL: {url}

CONTENT:
{content}

Provide a brief summary (2-3 paragraphs) covering the main points."""
)

# Safety limits to keep cost bounded
MAX_CHARS = int(os.environ.get("MAX_CHARS", "120000"))

# User agent for HTTP requests
UA = os.environ.get("USER_AGENT", "NotionSummarizerBot/1.0 (+https://github.com/yourusername/selfletter)")

# arXiv ID regex patterns
ARXIV_ID_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf|html)/)(\d{4}\.\d{4,5})(?:v\d+)?")
ARXIV_ID_RE2 = re.compile(r"arXiv:(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)

# Retry configuration
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))


def http_get(url: str, timeout: int = 45) -> str:
    """Fetch URL content with error handling."""
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    return r.text


def extract_arxiv_id(url: str) -> Optional[str]:
    """Extract arXiv ID from various URL formats."""
    m = ARXIV_ID_RE.search(url)
    if m:
        return m.group(1)
    m2 = ARXIV_ID_RE2.search(url)
    if m2:
        return m2.group(1)
    return None


def extract_readable_text_from_html(html: str) -> str:
    """Extract readable text from HTML, removing scripts/styles."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts/styles/noscript
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text("\n")
    # Normalize whitespace
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def fetch_blog_fulltext(url: str) -> str:
    """Fetch full article content using Trafilatura."""
    logger.info(f"Fetching blog content from: {url}")
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        logger.warning(f"Trafilatura failed, falling back to raw HTML: {url}")
        return extract_readable_text_from_html(http_get(url))

    extracted = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
    if extracted and extracted.strip():
        return extracted

    logger.warning(f"Trafilatura extraction empty, using raw HTML: {url}")
    return extract_readable_text_from_html(downloaded)


def fetch_arxiv_html_fulltext(arxiv_id: str) -> tuple[str, str]:
    """
    Fetch arXiv paper content.
    Returns (url_used, extracted_text).
    Tries official arXiv HTML endpoint first, falls back to abstract page.
    """
    logger.info(f"Fetching arXiv content for: {arxiv_id}")

    # Try official HTML endpoint
    html_url = f"https://arxiv.org/html/{arxiv_id}"
    try:
        html = http_get(html_url)
        text = extract_readable_text_from_html(html)
        if text.strip() and len(text) > 500:  # Basic sanity check
            logger.info(f"Successfully fetched HTML from: {html_url}")
            return html_url, text
        logger.warning(f"HTML content too short for {arxiv_id}")
    except Exception as e:
        logger.warning(f"Failed to fetch HTML for {arxiv_id}: {e}")

    # Fallback to abstract page
    logger.info(f"Falling back to abstract page for: {arxiv_id}")
    abs_url = f"https://arxiv.org/abs/{arxiv_id}"
    html = http_get(abs_url)
    text = extract_readable_text_from_html(html)
    return abs_url, text


def openai_summarize(title: str, url: str, content: str) -> str:
    """Generate summary using OpenAI API."""
    logger.info(f"Generating summary for: {title or url}")

    # Truncate content to stay within limits
    content = content[:MAX_CHARS]
    logger.info(f"Content length after truncation: {len(content)} chars")

    prompt = SUMMARY_PROMPT.format(title=title or "(untitled)", url=url, content=content)

    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}]
            }
        ]
    }

    try:
        r = requests.post(
            OPENAI_ENDPOINT,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()

        # Extract text from response
        out_texts = []
        for item in data.get("output", []):
            for c in item.get("content", []):
                if c.get("type") in ("output_text", "text"):
                    out_texts.append(c.get("text", ""))

        summary = "\n".join(t for t in out_texts if t).strip()
        return summary if summary else "(empty summary)"

    except requests.exceptions.RequestException as e:
        logger.error(f"OpenAI API error: {e}")
        raise RuntimeError(f"OpenAI API request failed: {e}")


def notion_rich_text(s: str, chunk: int = 1800) -> list[dict]:
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
        logger.error(f"Failed to set error on page {page_id}: {e}")


def increment_retry_count(notion: NotionClient, page_id: str):
    """Increment retry count on a Notion page."""
    try:
        count = get_retry_count({"properties": {PROP_RETRY: {"number": 0}}})
        notion.pages.update(
            page_id=page_id,
            properties={
                PROP_RETRY: {"number": count + 1},
            },
        )
    except Exception as e:
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


def create_summary_page(
    notion: NotionClient,
    title: str,
    source_url: str,
    typ: str,
    summary: str,
):
    """Create a summary page in the destination Notion database."""
    logger.info(f"Creating summary page for: {title or source_url}")

    now = datetime.now(timezone.utc).isoformat()

    properties = {
        DEST_PROP_TITLE: {"title": [{"type": "text", "text": {"content": (title or source_url)[:200] or "Untitled"}}]},
        DEST_PROP_URL: {"url": source_url},
        DEST_PROP_TYPE: {"select": {"name": typ}},
        DEST_PROP_SUMM: {"rich_text": notion_rich_text(summary[:9000])},
    }

    # Add date if property exists
    if DEST_PROP_DATE:
        try:
            properties[DEST_PROP_DATE] = {"date": {"start": now}}
        except Exception:
            pass

    notion.pages.create(
        parent={"database_id": DEST_DB_ID},
        properties=properties,
    )


def is_url_already_processed(notion: NotionClient, url: str) -> bool:
    """Check if a URL has already been processed in the destination DB."""
    try:
        response = notion.databases.query(
            database_id=DEST_DB_ID,
            filter={
                "property": DEST_PROP_URL,
                "url": {"equals": url}
            }
        )
        return len(response.get("results", [])) > 0
    except Exception:
        return False


def query_unprocessed(notion: NotionClient, page_size: int = 25) -> dict:
    """Query Notion for unprocessed pages."""
    return notion.databases.query(
        database_id=SOURCE_DB_ID,
        page_size=page_size,
        filter={
            "property": PROP_DONE,
            "checkbox": {"equals": False}
        }
    )


def process_one(notion: NotionClient, page: dict) -> bool:
    """Process a single Notion page."""
    page_id = page["id"]
    title = get_page_title(page)
    url = get_url_property(page)

    if not url:
        logger.warning(f"Page {page_id} missing URL property")
        safe_set_error(notion, page_id, f"Missing URL property '{PROP_URL}'.")
        mark_done(notion, page_id, done=True)
        return True  # Skip this page, no URL to process

    retry_count = get_retry_count(page)
    if retry_count >= MAX_RETRIES:
        logger.warning(f"Page {page_id} exceeded max retries ({MAX_RETRIES}), skipping")
        safe_set_error(notion, page_id, f"Max retries ({MAX_RETRIES}) exceeded")
        mark_done(notion, page_id, done=True)
        return True

    try:
        # Check if already processed
        if is_url_already_processed(notion, url):
            logger.info(f"URL already processed, skipping: {url}")
            mark_done(notion, page_id, done=True)
            return True

        arxiv_id = extract_arxiv_id(url)

        if arxiv_id:
            used_url, text = fetch_arxiv_html_fulltext(arxiv_id)
            typ = "arxiv"
            content_url = used_url
        else:
            text = fetch_blog_fulltext(url)
            typ = "blog"
            content_url = url

        if not text or len(text.strip()) < 200:
            raise RuntimeError(f"Extracted content too short ({len(text) if text else 0} chars)")

        logger.info(f"Content length for {typ}: {len(text)} chars")

        summary = openai_summarize(title=title, url=content_url, content=text)

        create_summary_page(
            notion=notion,
            title=title or content_url,
            source_url=content_url,
            typ=typ,
            summary=summary,
        )

        mark_done(notion, page_id, done=True)
        logger.info(f"Successfully processed: {title or url}")
        return True

    except Exception as e:
        logger.error(f"Error processing page {page_id}: {e}")
        safe_set_error(notion, page_id, f"{type(e).__name__}: {str(e)[:500]}")
        increment_retry_count(notion, page_id)
        time.sleep(1)
        return False


def main():
    """Main entry point."""
    logger.info("Starting Notion Summarizer")
    start_time = datetime.now()

    notion = NotionClient(auth=NOTION_TOKEN)

    try:
        resp = query_unprocessed(notion, page_size=25)
        results = resp.get("results", [])

        if not results:
            logger.info("No unprocessed items found")
            print(f"[{datetime.now(timezone.utc).isoformat()}] No items to process.")
            return

        logger.info(f"Found {len(results)} unprocessed items")

        success_count = 0
        for page in results:
            if process_one(notion, page):
                success_count += 1

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Processed {success_count}/{len(results)} items in {elapsed:.1f}s")
        print(f"[{datetime.now(timezone.utc).isoformat()}] Processed {success_count}/{len(results)} items in {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
