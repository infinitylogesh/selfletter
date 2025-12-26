# SelfLetter - Notion Summarizer

A "set-and-forget" Python script that:

1. Reads your **Notion "Inbox" database** for new links daily
2. Fetches full content from **arXiv papers** or **blog posts**
3. Summarizes using **OpenAI** (GPT-4o-mini for cost efficiency)
4. Writes summaries to a **Notion "Summaries" database**
5. Marks inbox items as processed

## Setup

### 1. Notion Setup

Create two Notion databases:

**Source DB ("Inbox") properties:**
- `URL` (url) - the paper/blog link
- `Summarized` (checkbox) - default unchecked
- `Last error` (rich_text, optional) - for debugging
- `Retry count` (number, optional) - tracks failed attempts

**Destination DB ("Summaries") properties:**
- `Name` (title) - article/paper title
- `Source URL` (url) - link to source
- `Type` (select) - values: `arxiv`, `blog`, `other`
- `Summary` (rich_text) - AI-generated summary
- `Added` (date, optional) - timestamp

### 2. Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Create a new integration
3. Copy the **Internal Integration Token**
4. Share both databases with the integration

### 3. Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `NOTION_TOKEN` - your Notion integration token
- `NOTION_SOURCE_DB_ID` - ID from the Inbox DB URL
- `NOTION_DEST_DB_ID` - ID from the Summaries DB URL
- `OPENAI_API_KEY` - your OpenAI API key

### 4. Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py
```

## Deployment (GitHub Actions - Free)

This project includes a GitHub Actions workflow for free daily execution:

1. Create a private repo and push this code
2. Add these secrets in GitHub repo Settings → Secrets:
   - `NOTION_TOKEN`
   - `NOTION_SOURCE_DB_ID`
   - `NOTION_DEST_DB_ID`
   - `OPENAI_API_KEY`
3. The workflow runs daily at 02:30 UTC automatically

## Configuration

Customize via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
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
└── README.md            # This file
```
