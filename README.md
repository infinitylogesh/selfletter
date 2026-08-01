# SelfLetter - Daily AI Papers Newsletter

A self-hosted newsletter service that fetches top papers from [HuggingFace Daily Papers](https://huggingface.co/papers), summarizes them using LLMs, and delivers a beautifully formatted newsletter.

## Features

- 📚 **Automatic Paper Fetching**: Fetches top N papers from HuggingFace Daily Papers
- 🤖 **AI-Powered Summaries**: Summarizes papers using OpenAI-compatible APIs
- 🎨 **Beautiful HTML Newsletters**: Renders markdown to stylish HTML with:
  - Responsive design with dark mode support
  - LaTeX/math rendering via KaTeX
  - Syntax-highlighted code blocks
  - Properly sized images
- 📧 **Flexible Delivery**: Supports multiple newsletter services:
  - Buttondown (recommended)
  - Email (SMTP)
  - Kit.com (formerly ConvertKit)
- 🔄 **Robust Fetching**: Uses Jina Reader with fallback to direct HTML parsing

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/infinitylogesh/selfletter.git
cd selfletter

# Create virtual environment (requires uv)
uv venv
source .venv/bin/activate
uv sync
```

### 2. Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

**Required variables:**
- `API_KEY` - Your OpenAI API key (or OpenRouter key)
- `ENDPOINT` - Chat completions endpoint (default: OpenRouter)
- `MODEL` - Model to use for summarization

**Paper fetching:**
- `TOP_PAPERS_COUNT` - Number of top papers to include (default: 5)
- `MIN_SUCCESSFUL_PAPERS` - Minimum successful summaries required to publish (default: 3)

**Newsletter delivery (choose one):**

For Buttondown:
- `NEWSLETTER_SERVICE=buttondown`
- `BUTTONDOWN_API_KEY` - API key from Buttondown settings
- `BUTTONDOWN_STATUS=draft` - Creates a reviewable draft; use `about_to_send` for automatic sending

For Email:
- `NEWSLETTER_SERVICE=email`
- `SMTP_USER`, `SMTP_PASS`, `EMAIL_TO`

For Kit.com:
- `NEWSLETTER_SERVICE=kit`
- `KIT_API_SECRET`

### 3. Run

```bash
PYTHONPATH=src python -m selfletter.cli
```

The service will:
1. Fetch yesterday's top papers from HuggingFace
2. Summarize each paper using the configured LLM
3. Generate a combined newsletter (markdown + HTML)
4. Send via your configured newsletter service

## Output

Newsletters are saved to the `newsletter/` directory:
```
newsletter/
└── 2026-01-25/
    ├── huggingface/
    │   ├── paper-title-1.md
    │   └── paper-title-2.md
    ├── daily-newsletter.md
    └── daily-newsletter.html
```

See [`examples/buttondown-sample.md`](examples/buttondown-sample.md) for a concise sample issue designed for Buttondown.

## Deployment (GitHub Actions)

This project includes a GitHub Actions workflow for daily execution:

1. Fork/clone to a private repository
2. Add secrets in Settings → Secrets → Actions:
   - `API_KEY`
   - `BUTTONDOWN_API_KEY`
3. Merge the workflow into the repository's default branch (`main`). GitHub only runs scheduled workflows from the default branch.
4. The workflow runs daily at 01:17 UTC and creates a Buttondown draft.

Buttondown requests use deterministic idempotency keys, so rerunning the same issue does not create a duplicate. When you are comfortable with fully automatic publishing, change `BUTTONDOWN_STATUS` in the workflow from `draft` to `about_to_send`.

To preview the bundled issue in Buttondown, manually run the workflow with **Create the bundled sample as a Buttondown draft** enabled. Samples are always created as drafts, regardless of the production publishing setting.

## Architecture

```
src/selfletter/
├── cli.py           # Main entry point
├── fetcher.py       # HuggingFace papers fetcher
├── renderer.py      # HTML newsletter renderer
├── combiner.py      # Combines summaries into newsletter
├── prompts.py       # LLM prompts
├── processors/      # Content processors (arXiv, HF, YouTube, etc.)
└── services/        # Newsletter delivery services
    ├── buttondown.py # Buttondown drafts and publishing
    ├── email.py     # SMTP email service
    └── kit.py       # Kit.com service
```

## Customization

### Summary Prompt

Edit `src/selfletter/prompts.py` to customize how papers are summarized.

### Newsletter Styling

Edit `src/selfletter/renderer.py` to customize the HTML template and CSS.

### Adding Newsletter Services

Implement the `NewsletterService` interface in `src/selfletter/services/`:

```python
from .base import NewsletterService

class MyService(NewsletterService):
    def send(self, subject, html_content, markdown_content=None):
        # Your implementation
        pass
    
    def validate_config(self):
        # Check required config
        pass
    
    @property
    def service_name(self):
        return "My Service"
```

## Acknowledgements

- [HuggingFace](https://huggingface.co) for the Daily Papers feature
- [Jina.ai](https://jina.ai) for the free Reader API
- [KaTeX](https://katex.org) for LaTeX rendering
- GitHub Actions for free daily execution

## License

MIT
