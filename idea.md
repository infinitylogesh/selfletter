Here’s a cheap, **Python-first**, “set-and-forget” setup that:

* reads a **Notion “Inbox” database** daily for new links
* pulls **full content** (blogs) and **HTML full paper** (arXiv, even if you paste abstract/PDF link)
* summarizes with **your custom prompt**
* writes results into a **second Notion “Summaries” database**
* marks the inbox item as processed

---

## 1) Notion database schema (simple + robust)

### Source DB (“Inbox”) properties

Create these properties in your source database:

* **URL** (type: `url`) — the paper/blog link you paste
* **Summarized** (type: `checkbox`) — default unchecked
* *(optional)* **Last error** (type: `rich_text`) — store failures for debugging

### Destination DB (“Summaries”) properties

* **Name** (type: `title`)
* **Source URL** (type: `url`)
* **Type** (type: `select`) values: `arxiv`, `blog`, `other`
* **Summary** (type: `rich_text`)
* *(optional)* **Added** (type: `date`)

### Notion integration

* Create a Notion integration + copy its token
* Share both databases with that integration

---

## 2) Content fetching rules

### arXiv links → HTML full paper

arXiv provides HTML versions for many papers (not all). They explicitly note some won’t have HTML, but many do. ([info.arxiv.org][1])
Your script should:

1. extract arXiv id from any of:

   * `arxiv.org/abs/<id>`
   * `arxiv.org/pdf/<id>.pdf`
   * `arxiv.org/html/<id>`
2. try: `https://arxiv.org/html/<id>` (official)
3. fallback: use the abstract page + (optionally) fetch PDF text if you want later (I’ll keep this version “HTML-first”, and fail gracefully if HTML doesn’t exist)

### Blogs → full readable content

Use a main-content extractor (Trafilatura) to get the article body, not just the HTML boilerplate.

---

## 3) Cheapest deployment option

### Option A (usually cheapest): **GitHub Actions cron (free)**

If you keep this in a private repo under a personal GitHub Free account, you get **2,000 Actions minutes/month** included. ([GitHub Docs][2])
A daily job that runs a few minutes is basically free.

> Note: GitHub announced pricing changes effective 2026 (including a platform charge for self-hosted runner usage), but the free quota stays the same. ([The GitHub Blog][3])

### Option B: Render cron job (paid but still cheap)

Render cron jobs have a **minimum $1/month**. ([Render][4])
Good if you don’t want GitHub.

---

## 4) LLM choice (lowest cost that still summarizes well)

For summarization, **gpt-4o-mini** is very cost-efficient: **$0.15 / 1M input tokens** and **$0.60 / 1M output tokens**. ([OpenAI Platform][5])
If you want even cheaper and can tolerate weaker summaries, **gpt-4.1-nano** is cheaper per token. ([OpenAI Platform][6])

---

## 5) Self-contained Python implementation

### `main.py`

```python
import os
import re
import time
import json
import requests
from datetime import datetime, timezone

# pip deps: notion-client, trafilatura, beautifulsoup4
from notion_client import Client as NotionClient
import trafilatura
from bs4 import BeautifulSoup

# ----------------------------
# Config (edit to match your DB property names)
# ----------------------------
SOURCE_DB_ID = os.environ["NOTION_SOURCE_DB_ID"]
DEST_DB_ID   = os.environ["NOTION_DEST_DB_ID"]

PROP_URL = os.environ.get("NOTION_PROP_URL", "URL")
PROP_DONE = os.environ.get("NOTION_PROP_DONE", "Summarized")
PROP_ERR = os.environ.get("NOTION_PROP_ERR", "Last error")  # optional

DEST_PROP_TITLE = os.environ.get("NOTION_DEST_PROP_TITLE", "Name")
DEST_PROP_URL   = os.environ.get("NOTION_DEST_PROP_URL", "Source URL")
DEST_PROP_TYPE  = os.environ.get("NOTION_DEST_PROP_TYPE", "Type")
DEST_PROP_SUMM  = os.environ.get("NOTION_DEST_PROP_SUMM", "Summary")

NOTION_TOKEN = os.environ["NOTION_TOKEN"]

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_ENDPOINT = os.environ.get("OPENAI_ENDPOINT", "https://api.openai.com/v1/responses")

# Your custom summarization prompt template.
# Use {title}, {url}, {content} placeholders.
SUMMARY_PROMPT = os.environ.get(
    "SUMMARY_PROMPT",
    "Summarize the following content.\n\nTitle: {title}\nURL: {url}\n\nCONTENT:\n{content}\n"
)

# Safety limits to keep cost bounded
MAX_CHARS = int(os.environ.get("MAX_CHARS", "120000"))  # trim large pages

UA = os.environ.get("USER_AGENT", "NotionSummarizerBot/1.0")

ARXIV_ID_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf|html)/)(\d{4}\.\d{4,5})(?:v\d+)?")
ARXIV_ID_RE2 = re.compile(r"arXiv:(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)

def http_get(url: str, timeout=45) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    return r.text

def extract_arxiv_id(url: str) -> str | None:
    m = ARXIV_ID_RE.search(url)
    if m:
        return m.group(1)
    m2 = ARXIV_ID_RE2.search(url)
    if m2:
        return m2.group(1)
    return None

def extract_readable_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # remove scripts/styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text("\n")
    # normalize whitespace
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)

def fetch_blog_fulltext(url: str) -> str:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        # fallback: raw HTML to text
        return extract_readable_text_from_html(http_get(url))

    extracted = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
    if extracted and extracted.strip():
        return extracted
    return extract_readable_text_from_html(downloaded)

def fetch_arxiv_html_fulltext(arxiv_id: str) -> tuple[str, str]:
    """
    Returns (html_url_used, extracted_text).
    Tries official arXiv HTML endpoint first.
    """
    html_url = f"https://arxiv.org/html/{arxiv_id}"
    try:
        html = http_get(html_url)
        text = extract_readable_text_from_html(html)
        if text.strip():
            return html_url, text
    except Exception:
        pass

    # If no HTML available, still return something useful: abstract page text
    abs_url = f"https://arxiv.org/abs/{arxiv_id}"
    html = http_get(abs_url)
    text = extract_readable_text_from_html(html)
    return abs_url, text

def openai_summarize(title: str, url: str, content: str) -> str:
    content = content[:MAX_CHARS]

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

    # responses API returns a list of output items; grab text
    out_texts = []
    for item in data.get("output", []):
        for c in item.get("content", []):
            if c.get("type") in ("output_text", "text"):
                out_texts.append(c.get("text", ""))
    summary = "\n".join(t for t in out_texts if t).strip()
    return summary or "(empty summary)"

def notion_rich_text(s: str, chunk=1800):
    # Notion has per-block limits; keep chunks small
    s = s or ""
    parts = [s[i:i+chunk] for i in range(0, len(s), chunk)]
    return [{"type": "text", "text": {"content": p}} for p in parts] or [{"type":"text","text":{"content":""}}]

def get_page_title(page: dict) -> str:
    # page["properties"] has a title property (unknown name). We'll try to find it.
    props = page.get("properties", {})
    for k, v in props.items():
        if v.get("type") == "title":
            title_arr = v.get("title", [])
            return "".join(t.get("plain_text","") for t in title_arr).strip()
    return ""

def get_url_property(page: dict) -> str | None:
    props = page.get("properties", {})
    p = props.get(PROP_URL)
    if not p:
        return None
    if p.get("type") == "url":
        return p.get("url")
    return None

def safe_set_error(notion: NotionClient, page_id: str, msg: str):
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                PROP_ERR: {"rich_text": notion_rich_text(msg[:4000])},
            },
        )
    except Exception:
        pass

def mark_done(notion: NotionClient, page_id: str, done=True):
    notion.pages.update(
        page_id=page_id,
        properties={
            PROP_DONE: {"checkbox": bool(done)}
        },
    )

def create_summary_page(notion: NotionClient, title: str, source_url: str, typ: str, summary: str):
    notion.pages.create(
        parent={"database_id": DEST_DB_ID},
        properties={
            DEST_PROP_TITLE: {"title": [{"type": "text", "text": {"content": title[:200] or "Untitled"}}]},
            DEST_PROP_URL: {"url": source_url},
            DEST_PROP_TYPE: {"select": {"name": typ}},
            DEST_PROP_SUMM: {"rich_text": notion_rich_text(summary[:9000])},
        },
    )

def query_unprocessed(notion: NotionClient, page_size=25):
    return notion.databases.query(
        database_id=SOURCE_DB_ID,
        page_size=page_size,
        filter={
            "property": PROP_DONE,
            "checkbox": {"equals": False}
        }
    )

def process_one(notion: NotionClient, page: dict):
    page_id = page["id"]
    title = get_page_title(page)
    url = get_url_property(page)

    if not url:
        safe_set_error(notion, page_id, f"Missing URL property '{PROP_URL}'.")
        mark_done(notion, page_id, done=True)
        return

    try:
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
            raise RuntimeError("Extracted content is too short; page may be blocked or empty.")

        summary = openai_summarize(title=title, url=content_url, content=text)

        create_summary_page(
            notion=notion,
            title=title or content_url,
            source_url=content_url,
            typ=typ,
            summary=summary
        )

        mark_done(notion, page_id, done=True)

    except Exception as e:
        safe_set_error(notion, page_id, f"{type(e).__name__}: {e}")
        # leave unprocessed so it retries tomorrow (or you can mark done=False)
        time.sleep(1)

def main():
    notion = NotionClient(auth=NOTION_TOKEN)

    resp = query_unprocessed(notion, page_size=25)
    results = resp.get("results", [])

    for page in results:
        process_one(notion, page)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Processed {len(results)} items.")

if __name__ == "__main__":
    main()
```

### `requirements.txt`

```txt
notion-client==2.2.1
requests==2.32.3
trafilatura==1.9.0
beautifulsoup4==4.12.3
lxml==5.3.0
```

---

## 6) GitHub Actions daily cron (recommended)

Create `.github/workflows/daily.yml`:

```yaml
name: Notion daily summarizer

on:
  schedule:
    - cron: "30 2 * * *"  # runs daily at 02:30 UTC
  workflow_dispatch: {}

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run summarizer
        env:
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          NOTION_SOURCE_DB_ID: ${{ secrets.NOTION_SOURCE_DB_ID }}
          NOTION_DEST_DB_ID: ${{ secrets.NOTION_DEST_DB_ID }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          OPENAI_MODEL: "gpt-4o-mini"
          NOTION_PROP_URL: "URL"
          NOTION_PROP_DONE: "Summarized"
          NOTION_PROP_ERR: "Last error"
          NOTION_DEST_PROP_TITLE: "Name"
          NOTION_DEST_PROP_URL: "Source URL"
          NOTION_DEST_PROP_TYPE: "Type"
          NOTION_DEST_PROP_SUMM: "Summary"
          SUMMARY_PROMPT: |
            You are my research assistant.
            Produce:
            1) TL;DR (3 bullets)
            2) Key contributions (5 bullets)
            3) Methods / architecture (short)
            4) Results (numbers if present)
            5) Limitations + follow-ups
            Keep it crisp, no fluff.

            Title: {title}
            URL: {url}

            CONTENT:
            {content}
        run: |
          python main.py
```

**Why this is “cheap”:** GitHub Free includes **2,000 minutes/month** for private repos, which is plenty for a once-a-day Python run. ([GitHub Docs][2])

---

## 7) Cost expectations (rough)

Using **gpt-4o-mini** pricing ([OpenAI Platform][5]):

* If you summarize ~1–3 papers/posts per day and trim to ~50k–120k chars, you’ll usually land in “pennies to a couple dollars/month” territory unless you ingest *very* long posts/papers daily.

If you want to push cost further down:

* set `MAX_CHARS` lower (e.g., 60k)
* use `gpt-4.1-nano` (cheaper) ([OpenAI Platform][6])
* or do a two-stage prompt: extract “important sections” first, then summarize that

---

## 8) Practical improvements (worth doing)

* Add a “Retry count” number property so failures don’t loop forever.
* Store the summary as page content blocks (not just a property) if you want nicer reading in Notion.
* Add dedupe: hash the URL + skip if already exists in destination DB.

---

If you tell me your **exact Notion property names** (or paste a screenshot of the DB schema), I can tailor the script so you don’t have to touch the mapping section at all.

[1]: https://info.arxiv.org/about/accessible_HTML.html "accessible HTML - arXiv info"
[2]: https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions "GitHub Actions billing - GitHub Docs"
[3]: https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/ "Update to GitHub Actions pricing - GitHub Changelog"
[4]: https://render.com/docs/cronjobs "Cron Jobs – Render Docs"
[5]: https://platform.openai.com/docs/models/compare?model=gpt-4o-mini "Compare models | OpenAI API"
[6]: https://platform.openai.com/docs/pricing "Pricing | OpenAI API"
