"""Create a safe Buttondown draft from the bundled sample issue."""

import os
from pathlib import Path

from .renderer import render_newsletter
from .services import get_service


def main() -> None:
    newsletter_name = os.environ.get("NEWSLETTER_NAME", "Daily AI Papers")
    sample_path = Path(
        os.environ.get("SAMPLE_NEWSLETTER_PATH", "examples/buttondown-sample.md")
    )
    markdown_content = sample_path.read_text()
    html_content = render_newsletter(
        markdown_content,
        date="Sample issue",
        newsletter_name=newsletter_name,
    )

    # Samples are always drafts, even after production publishing is automated.
    service = get_service("buttondown", status="draft")
    if not service.validate_config():
        raise RuntimeError("BUTTONDOWN_API_KEY is required")

    success = service.send(
        subject=f"SAMPLE — {newsletter_name}",
        html_content=html_content,
        markdown_content=markdown_content,
    )
    if not success:
        raise RuntimeError("Failed to create Buttondown sample draft")


if __name__ == "__main__":
    main()
