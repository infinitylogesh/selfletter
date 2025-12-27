"""
Content processor factory.
Automatically selects the appropriate processor based on URL.
"""

import logging
from typing import Optional
from .base import BaseProcessor
from .arxiv import ArxivProcessor
from .huggingface import HuggingFaceProcessor
from .youtube import YouTubeProcessor
from .article import ArticleProcessor

logger = logging.getLogger(__name__)


class ProcessorFactory:
    """Factory for creating appropriate content processors."""
    
    def __init__(self, openai_api_key: str, openai_model: str, openai_endpoint: str,
                 summary_prompt: str, max_chars: int = 120000, user_agent: str = "SelfLetterBot/1.0"):
        """Initialize factory with common configuration."""
        self.config = {
            "openai_api_key": openai_api_key,
            "openai_model": openai_model,
            "openai_endpoint": openai_endpoint,
            "summary_prompt": summary_prompt,
            "max_chars": max_chars,
            "user_agent": user_agent,
        }
        
        # Order matters: more specific processors first, generic last
        self.processor_classes = [
            HuggingFaceProcessor,  # Check HF before arXiv (HF URLs contain arXiv IDs)
            ArxivProcessor,
            YouTubeProcessor,
            ArticleProcessor,  # Fallback - handles everything
        ]
    
    def get_processor(self, url: str) -> BaseProcessor:
        """
        Get appropriate processor for the given URL.
        Returns the first processor that can handle the URL.
        """
        for processor_class in self.processor_classes:
            processor = processor_class(**self.config)
            if processor.can_handle(url):
                logger.info(f"Selected processor: {processor_class.__name__} for URL: {url}")
                return processor
        
        # Should never reach here since ArticleProcessor handles everything
        logger.warning(f"No processor found for URL: {url}, using ArticleProcessor")
        return ArticleProcessor(**self.config)


__all__ = [
    'ProcessorFactory',
    'BaseProcessor',
    'ArxivProcessor',
    'HuggingFaceProcessor',
    'YouTubeProcessor',
    'ArticleProcessor',
]

