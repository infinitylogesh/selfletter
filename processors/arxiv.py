"""
arXiv content processor for both PDF and abstract pages.
"""

import re
import logging
from typing import Tuple
from .base import BaseProcessor

logger = logging.getLogger(__name__)


class ArxivProcessor(BaseProcessor):
    """Processor for arXiv papers (PDF and abstract pages)."""
    
    ARXIV_ID_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf|html)/)(\d{4}\.\d{4,5})(?:v\d+)?")
    ARXIV_ID_RE2 = re.compile(r"arXiv:(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)
    
    def can_handle(self, url: str) -> bool:
        """Check if URL is an arXiv link."""
        return bool(self._extract_arxiv_id(url))
    
    def get_content_type(self) -> str:
        """Return content type identifier."""
        return "arxiv"
    
    def _extract_arxiv_id(self, url: str) -> str:
        """Extract arXiv ID from URL."""
        m = self.ARXIV_ID_RE.search(url)
        if m:
            return m.group(1)
        m2 = self.ARXIV_ID_RE2.search(url)
        if m2:
            return m2.group(1)
        return None
    
    def extract_content(self, url: str) -> Tuple[str, str, str]:
        """
        Extract content from arXiv paper.
        Tries HTML version first, then PDF version, falls back to abstract page.
        """
        arxiv_id = self._extract_arxiv_id(url)
        if not arxiv_id:
            raise ValueError(f"Could not extract arXiv ID from URL: {url}")
        
        logger.info(f"Processing arXiv paper: {arxiv_id}")
        
        # 1. Try HTML version first (best for content extraction)
        html_url = f"https://arxiv.org/html/{arxiv_id}"
        try:
            content = self.fetch_with_jina(html_url)
            
            # Check for common "HTML not available" patterns in the Jina output
            error_markers = ["error 404", "no html for", "html is not available for the source"]
            content_lower = content.lower()
            is_error_page = any(marker in content_lower for marker in error_markers)
            
            if content and len(content.strip()) > 500 and not is_error_page:
                logger.info(f"Successfully fetched arXiv HTML version: {arxiv_id}")
                title = self._extract_title_from_content(content, arxiv_id)
                return title, content, html_url
            
            if is_error_page:
                logger.warning(f"arXiv HTML version for {arxiv_id} seems to be an error page. Falling back.")
        except Exception as e:
            logger.warning(f"Failed to fetch HTML version for {arxiv_id}: {e}")
        
        # 2. Try PDF version via Jina Reader
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        try:
            logger.info(f"Trying PDF version for: {arxiv_id}")
            content = self.fetch_with_jina(pdf_url)
            if content and len(content.strip()) > 500:
                logger.info(f"Successfully fetched arXiv PDF version: {arxiv_id}")
                title = self._extract_title_from_content(content, arxiv_id)
                return title, content, pdf_url
        except Exception as e:
            logger.warning(f"Failed to fetch PDF version for {arxiv_id}: {e}")

        # 3. Fallback to abstract page
        logger.info(f"Falling back to abstract page for: {arxiv_id}")
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        content = self.fetch_with_jina(abs_url)
        title = self._extract_title_from_content(content, arxiv_id)
        
        return title, content, abs_url
    
    def _extract_title_from_content(self, content: str, arxiv_id: str) -> str:
        """Extract title from content text."""
        # Jina Reader typically puts title at the beginning
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line and len(line) > 10 and len(line) < 200:
                # Skip common headers
                if line.lower() not in ['abstract', 'arxiv', 'title']:
                    return line
        
        # Fallback to arXiv ID
        return f"arXiv:{arxiv_id}"
