import logging
import re
from typing import Optional
from notion_client import Client as NotionClient

logger = logging.getLogger(__name__)

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


def get_url_property(page: dict, prop_name: str) -> Optional[str]:
    """Extract URL from a Notion page property."""
    props = page.get("properties", {})
    p = props.get(prop_name)
    if not p:
        return None
    if p.get("type") == "url":
        return p.get("url")
    return None


def get_retry_count(page: dict, prop_name: str) -> int:
    """Get current retry count from page."""
    props = page.get("properties", {})
    p = props.get(prop_name)
    if p and p.get("type") == "number":
        return p.get("number") or 0
    return 0


def safe_set_error(notion: NotionClient, page_id: str, prop_err: str, msg: str):
    """Safely set error message on a Notion page."""
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                prop_err: {"rich_text": notion_rich_text(msg[:4000])},
            },
        )
    except Exception as e:
        err_msg = str(e)
        if "does not exist" in err_msg:
            logger.warning(f"Error property '{prop_err}' not found in Notion database. Skipping error logging to Notion.")
        else:
            logger.error(f"Failed to set error on page {page_id}: {e}")


def increment_retry_count(notion: NotionClient, page_id: str, prop_retry: str, current_count: int):
    """Increment retry count on a Notion page."""
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                prop_retry: {"number": current_count + 1},
            },
        )
    except Exception as e:
        err_msg = str(e)
        if "does not exist" in err_msg:
            logger.warning(f"Retry count property '{prop_retry}' not found in Notion database. Skipping.")
        else:
            logger.warning(f"Failed to increment retry count: {e}")


def mark_done(notion: NotionClient, page_id: str, prop_done: str, done: bool = True):
    """Mark a page as processed."""
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                prop_done: {"checkbox": bool(done)}
            },
        )
    except Exception as e:
        logger.error(f"Failed to mark page {page_id} as done: {e}")

