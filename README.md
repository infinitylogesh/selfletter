# SelfLetter - Local Newsletter Summarizer

A "set-and-forget" Python script that:

1. Reads your **Notion "Inbox" database** for new links daily
2. Fetches full content from **arXiv papers** or **blog posts**
3. Summarizes using **OpenAI** (GPT-4o-mini for cost efficiency)
4. Writes summaries to **local markdown files** organized by date
5. Marks inbox items as processed

## Folder Structure

```
selfletter/
├── newsletter/
│   ├── 2025-12-26/
│   │   ├── arxiv/
│   │   │   └── attention-is-all-you-need.md
│   │   └── blog/
│   │       └── building-better-apis.md
│   └── 2025-12-27/
│       └── ...
├── main.py
└── ...
```

## Setup

### 1. Notion Setup (Source Only)

Create a Notion database with these properties:

**Source DB ("Inbox") properties:**
- `URL` (url) - the paper/blog link
- `Summarized` (checkbox) - default unchecked
- `Last error` (rich_text, optional) - for debugging
- `Retry count` (number, optional) - tracks failed attempts

### 2. Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Create a new integration
3. Copy the **Internal Integration Token**
4. Share the Inbox database with the integration

### 3. Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `NOTION_TOKEN` - your Notion integration token
- `NOTION_SOURCE_DB_ID` - ID from the Inbox DB URL
- `OPENAI_API_KEY` - your OpenAI API key

Optional:
- `OUTPUT_DIR` - output directory (default: `newsletter`)

### 4. Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py
```

## Output Format

Summaries are saved as markdown files with YAML frontmatter:

```markdown
---
title: "Paper Title"
source_url: "https://arxiv.org/abs/..."
type: "arxiv"
date: "2025-12-26T10:30:00+00:00"
---

AI-generated summary text goes here...
```

## Deployment (GitHub Actions - Free)

This project includes a GitHub Actions workflow for free daily execution:

1. Create a private repo and push this code
2. Add these secrets in GitHub repo Settings → Secrets:
   - `NOTION_TOKEN`
   - `NOTION_SOURCE_DB_ID`
   - `OPENAI_API_KEY`
3. The workflow runs daily at 02:30 UTC automatically
4. Optionally add `OUTPUT_DIR` if you want a different output folder name

## Configuration

Customize via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_DIR` | `newsletter` | Directory for saved summaries |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model for summarization |
| `MAX_CHARS` | `120000` | Max content characters to send to OpenAI |
| `MAX_RETRIES` | `3` | Max retry attempts per page |
| `SUMMARY_PROMPT` | (see code) | Custom prompt template |
| `NOTION_PROP_*` | (see code) | Property name mappings |

## Cost Estimate

Using GPT-4o-mini:
- ~$0.15 per 1M input tokens
- ~$0.60 per 1M output tokens
- Summarizing 1-3 papers/day: **$1-3/month**

## Project Structure

```
selfletter/
├── main.py              # Main application
├── requirements.txt     # Python dependencies
├── .github/workflows/   # GitHub Actions
│   └── daily.yml
├── .env.example         # Environment template
├── README.md            # This file
└── newsletter/          # Generated summaries (gitignored)
```
