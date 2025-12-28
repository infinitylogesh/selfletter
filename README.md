# SelfLetter - A one-person newsletter for yourself

A self newsletter service built for my personal use to cope with the pace of AI research progress. 

Feel free to try the repo and fork it to adapt to your needs.  Keep in mind that this was created to suit my workflow ( and my chaos), if you like to adapt to yours - you can do it by fitting your workflow in `src/selfletter/cli.py`

This service reads URLs clipped / added to a notion database and summarizes the contents ( based on this [prompt](https://github.com/infinitylogesh/selfletter/blob/main/src/selfletter/prompts.py)) , sends a daily digest as a newsletter to my mail box.

I have written more about the intention [here](https://logeshumapathi.com/blog/2025/12/28/selfletter.html)


### Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Create a new integration
3. Copy the **Internal Integration Token**
4. Share the Inbox database with the integration

### Email Integration

The service is tested to work with gmail using the [Google application password](https://support.google.com/accounts/answer/185833?hl=en)

### Processors:

The service supports URL processing for these links:

- `Arxiv`: Arxiv abstract , pdf , html urls
- `Huggingface pages`: Hugginface page to full paper content
- `Blog post URLs`
- `Youtube Videos`

All text content are parsed from source using `r.jina.ai` endpoint to fetch LLM suitable format.

### 3. Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `NOTION_TOKEN` - your Notion integration token
- `NOTION_SOURCE_DB_ID` - ID from the Inbox DB URL 
- `API_KEY` - your OpenAI API key
- `ENDPOINT` - openai compatible / Openrouter chat completion endpoint 
- `MODEL` - model you want to use, ex. `openai/gpt-oss-120b`.
- `SMTP_USER` - your email id
- `SMTP_PASS` - your application password from gmail
- `EMAIL_TO` -  your email id

Optional:
- `OUTPUT_DIR` - output directory (default: `newsletter`)

### 4. Setup and Local Testing

Setup:

```bash
# make sure you have `uv` installed
# (see https://docs.astral.sh/uv/getting-started/installation/)
git clone https://github.com/infinitylogesh/selfletter.git

uv venv
source .venv/bin/activate
uv sync
```

Testing:

```bash
# cd selfletter
PYTHONPATH=src python -m selfletter.cli
```

## Deployment (GitHub Actions)

This project includes a GitHub Actions workflow for free daily execution:

1. Create a private repo and push this code
2. Add all the env variables as secrets in `.github/workflows/daily.yml`
3. The workflow runs daily at 01:00 UTC automatically


## Acknowledgement and Gratitude:

- Thanks to [Jina.ai](http://Jina.ai)  for the free reader endpoint
- Thanks to Github Actions service for making this service simpler.
- Thanks to Andrew Ng's [advice](https://youtu.be/733m6qBH-jI?t=830). The prompt is based on the advice.
- This repo was mostly vibe coded with [Blackbox Cli](https://docs.blackbox.ai/features/blackbox-cli/introduction)
