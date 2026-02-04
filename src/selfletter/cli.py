#!/usr/bin/env python3
"""
SelfLetter CLI - Fetches daily papers from HuggingFace and creates a newsletter.
"""

import os
import re
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

from .prompts import SUMMARY as SUMMARY_PROMPT
from .processors import ProcessorFactory
from .combiner import NewsletterCombiner
from .fetcher import PaperFetcher, Paper
from .renderer import render_newsletter
from .services import get_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def get_config():
    """Load configuration from environment variables."""
    load_dotenv()
    return {
        "API_KEY": os.environ.get("API_KEY"),
        "OUTPUT_DIR": os.environ.get("OUTPUT_DIR", "newsletter"),
        "MODEL": os.environ.get("MODEL", "gpt-4o-mini"),
        "ENDPOINT": os.environ.get("ENDPOINT", "https://openrouter.ai/api/v1/chat/completions"),
        "MAX_CHARS": int(os.environ.get("MAX_CHARS", "200000")),
        "USER_AGENT": os.environ.get("USER_AGENT", "SelfLetterBot/1.0"),
        "TOP_PAPERS_COUNT": int(os.environ.get("TOP_PAPERS_COUNT", "5")),
        "NEWSLETTER_SERVICE": os.environ.get("NEWSLETTER_SERVICE", "email"),
        "NEWSLETTER_NAME": os.environ.get("NEWSLETTER_NAME", "Daily AI Papers"),
        "SCHEDULE_MINUTES": int(os.environ.get("SCHEDULE_MINUTES", "0")),
    }


def sanitize_filename(name: str) -> str:
    """Convert title to safe filename."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name[:100] if name else "untitled"


def save_summary_to_file(
    output_dir: str,
    title: str,
    source_url: str,
    typ: str,
    summary: str,
    date_str: str = None
) -> Path:
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
    return filepath


def process_paper(
    paper: Paper,
    processor_factory: ProcessorFactory,
    config: dict,
    date_str: str
) -> bool:
    """
    Process a single paper: fetch content and generate summary.
    
    Returns:
        True if processed successfully, False otherwise
    """
    logger.info(f"Processing paper: {paper.title} ({paper.arxiv_id})")
    
    try:
        # Use the HuggingFace paper URL which will be handled by HuggingFaceProcessor
        url = paper.hf_url
        
        processor = processor_factory.get_processor(url)
        final_title, content_type, actual_url, summary = processor.process(url, paper.title)
        
        save_summary_to_file(
            config["OUTPUT_DIR"],
            title=final_title,
            source_url=actual_url,
            typ=content_type,
            summary=summary,
            date_str=date_str,
        )
        
        logger.info(f"Successfully processed: {final_title}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing paper {paper.arxiv_id}: {e}")
        return False


def main():
    """Main entry point."""
    config = get_config()

    # Use yesterday's date for papers (they're usually available the next day)
    yesterday = datetime.now() - timedelta(days=1)
    paper_date = yesterday.strftime("%Y-%m-%d")
    combiner = NewsletterCombiner(output_dir=config["OUTPUT_DIR"])


    # check if newsletter exists for the given date
    newsletter_path = Path(config["OUTPUT_DIR"]) / paper_date / "daily-newsletter.md"
    if newsletter_path.exists():
        markdown_content = newsletter_path.read_text()
        html_content = render_newsletter(
            markdown_content,
            date=paper_date,
            newsletter_name=config["NEWSLETTER_NAME"]
        )
        html_path = newsletter_path.with_suffix('.html')
        html_path.write_text(html_content)
        logger.info(f"Newsletter already exists for {paper_date}")
        
        # send newsletter
        newsletter_service = get_service(config["NEWSLETTER_SERVICE"])
        
        # Calculate send_at if scheduling is enabled
        send_at = None
        if config["SCHEDULE_MINUTES"] > 0:
            send_at = datetime.now(timezone.utc) + timedelta(minutes=config["SCHEDULE_MINUTES"])
            logger.info(f"Scheduling newsletter for {send_at.isoformat()}")
        
        newsletter_service.send(
            subject=f"{config['NEWSLETTER_NAME']} - {paper_date}",
            html_content=html_content,
            markdown_content=markdown_content,
            send_at=send_at
        )
        logger.info("Newsletter sent successfully!")
        return
    
    # else, proceed to fetch and process papers
    # Validate required config
    if not config["API_KEY"]:
        logger.error("API_KEY environment variable is required")
        return
    
    logger.info("Starting SelfLetter Daily Papers Digest")
    start_time = datetime.now()
    
    # Initialize components
    fetcher = PaperFetcher(user_agent=config["USER_AGENT"])
    
    processor_factory = ProcessorFactory(
        openai_api_key=config["API_KEY"],
        openai_model=config["MODEL"],
        openai_endpoint=config["ENDPOINT"],
        summary_prompt=SUMMARY_PROMPT,
        max_chars=config["MAX_CHARS"],
        user_agent=config["USER_AGENT"],
    )
    
    
    # Get newsletter service
    try:
        newsletter_service = get_service(config["NEWSLETTER_SERVICE"])
        logger.info(f"Using newsletter service: {newsletter_service.service_name}")
    except ValueError as e:
        logger.error(f"Invalid newsletter service: {e}")
        return
    
    try:
        
        logger.info(f"Fetching top {config['TOP_PAPERS_COUNT']} papers for {paper_date}")
        
        # Fetch daily papers
        papers = fetcher.fetch_daily_papers(
            date=paper_date,
            top_n=config["TOP_PAPERS_COUNT"]
        )
        
        if not papers:
            logger.warning(f"No papers found for {paper_date}")
            return
        
        logger.info(f"Found {len(papers)} papers to process")
        for i, paper in enumerate(papers, 1):
            logger.info(f"  {i}. {paper.title} (upvotes: {paper.upvotes})")
        
        # Process each paper
        success_count = 0
        for paper in papers:
            if process_paper(paper, processor_factory, config, paper_date):
                success_count += 1
            # Small delay between papers to avoid rate limiting
            time.sleep(2)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Processed {success_count}/{len(papers)} papers in {elapsed:.1f}s")
        
        if success_count > 0:
            # Combine summaries into newsletter
            logger.info("Combining summaries into newsletter...")
            newsletter_path = combiner.combine_daily_summaries(paper_date)
            
            if newsletter_path:
                logger.info(f"Newsletter created: {newsletter_path}")
                
                # Read markdown content
                markdown_content = Path(newsletter_path).read_text()
                
                # Render to HTML
                html_content = render_newsletter(
                    markdown_content,
                    date=paper_date,
                    newsletter_name=config["NEWSLETTER_NAME"]
                )
                
                # Save HTML version
                html_path = Path(newsletter_path).with_suffix('.html')
                html_path.write_text(html_content)
                logger.info(f"HTML newsletter saved: {html_path}")
                
                # Send newsletter
                subject = f"{config['NEWSLETTER_NAME']} - {paper_date}"
                
                if newsletter_service.validate_config():
                    # Calculate send_at if scheduling is enabled
                    send_at = None
                    if config["SCHEDULE_MINUTES"] > 0:
                        send_at = datetime.now(timezone.utc) + timedelta(minutes=config["SCHEDULE_MINUTES"])
                        logger.info(f"Scheduling newsletter for {send_at.isoformat()}")
                    
                    success = newsletter_service.send(
                        subject=subject,
                        html_content=html_content,
                        markdown_content=markdown_content,
                        send_at=send_at
                    )
                    if success:
                        logger.info("Newsletter sent successfully!")
                    else:
                        logger.error("Failed to send newsletter")
                else:
                    logger.warning(
                        f"Newsletter service ({newsletter_service.service_name}) not configured. "
                        "Newsletter saved locally but not sent."
                    )
        else:
            logger.warning("No papers were successfully processed")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
