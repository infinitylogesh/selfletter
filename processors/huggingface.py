"""
HuggingFace papers processor.
Extracts arXiv ID from HuggingFace paper URL and fetches the paper.
"""

import re
import logging
from typing import Tuple
from .arxiv import ArxivProcessor

logger = logging.getLogger(__name__)


class HuggingFaceProcessor(ArxivProcessor):
    """Processor for HuggingFace papers (redirects to arXiv)."""
    
    HF_PAPER_RE = re.compile(r"huggingface\.co/papers/(\d{4}\.\d{4,5})")
    
    def can_handle(self, url: str) -> bool:
        """Check if URL is a HuggingFace paper link."""
        return bool(self.HF_PAPER_RE.search(url))
    
    def get_content_type(self) -> str:
        """Return content type identifier."""
        return "huggingface"
    
    def _extract_hf_arxiv_id(self, url: str) -> str:
        """Extract arXiv ID from HuggingFace URL."""
        m = self.HF_PAPER_RE.search(url)
        if m:
            return m.group(1)
        return None
    
    def extract_content(self, url: str) -> Tuple[str, str, str]:
        """
        Extract content from HuggingFace paper.
        Extracts arXiv ID and fetches the paper from arXiv.
        """
        arxiv_id = self._extract_hf_arxiv_id(url)
        if not arxiv_id:
            raise ValueError(f"Could not extract arXiv ID from HuggingFace URL: {url}")
        
        logger.info(f"Processing HuggingFace paper (arXiv: {arxiv_id})")
        
        # Use parent class method to fetch arXiv content
        # This will now correctly use ArxivProcessor._extract_arxiv_id 
        # because we no longer override that method name.
        return super().extract_content(f"https://arxiv.org/abs/{arxiv_id}")
