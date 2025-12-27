"""
Generic article processor for blog posts and other web content.
"""

import logging
from typing import Tuple
from .base import BaseProcessor

logger = logging.getLogger(__name__)


class ArticleProcessor(BaseProcessor):
    """Processor for generic articles and blog posts."""
    
    def can_handle(self, url: str) -> bool:
        """This is the fallback processor, handles all URLs."""
        return True
    
    def get_content_type(self) -> str:
        """Return content type identifier."""
        return "article"
    
    def extract_content(self, url: str) -> Tuple[str, str, str]:
        """
        Extract content from generic article/blog post.
        Uses Jina Reader for clean content extraction.
        """
        logger.info(f"Processing article: {url}")
        
        try:
            content = self.fetch_with_jina(url)
            
            # Extract title from content
            title = self._extract_title_from_content(content, url)
            
            logger.info(f"Successfully extracted article content from: {url}")
            return title, content, url
            
        except Exception as e:
            logger.error(f"Failed to extract article content from {url}: {e}")
            raise RuntimeError(f"Failed to process article: {e}")
    
    def _extract_title_from_content(self, content: str, url: str) -> str:
        """Extract title from content text."""
        lines = content.split('\n')
        
        # Look for title in first few lines
        for line in lines[:10]:
            line = line.strip()
            # Title is usually a longer line (but not too long)
            if line and 20 < len(line) < 200:
                # Skip lines that look like metadata
                if not any(x in line.lower() for x in ['published', 'author:', 'date:', 'by ', '|']):
                    return line
        
        # Fallback: use domain name from URL
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return f"Article from {domain}"
        except:
            return url

