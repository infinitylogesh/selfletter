"""
HuggingFace Daily Papers Fetcher.
Fetches top papers from https://huggingface.co/papers/date/{date}
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """Represents a paper from HuggingFace daily papers."""
    title: str
    arxiv_id: str
    url: str
    upvotes: int = 0
    thumbnail: Optional[str] = None
    
    @property
    def arxiv_url(self) -> str:
        """Get the arXiv abstract URL."""
        return f"https://arxiv.org/abs/{self.arxiv_id}"
    
    @property
    def hf_url(self) -> str:
        """Get the HuggingFace paper URL."""
        return f"https://huggingface.co/papers/{self.arxiv_id}"


class PaperFetcher:
    """Fetches daily papers from HuggingFace."""
    
    JINA_BASE_URL = "https://r.jina.ai/"
    HF_PAPERS_URL = "https://huggingface.co/papers"
    
    def __init__(self, user_agent: str = "SelfLetterBot/1.0", timeout: int = 60):
        self.user_agent = user_agent
        self.timeout = timeout
    
    def fetch_daily_papers(self, date: str, top_n: int = 5) -> List[Paper]:
        """
        Fetch top N papers for a given date.
        
        Args:
            date: Date string in YYYY-MM-DD format
            top_n: Number of top papers to return
        
        Returns:
            List of Paper objects sorted by upvotes (descending)
        """
        logger.info(f"Fetching daily papers for {date}, top {top_n}")
        
        # Try Jina Reader first
        try:
            papers = self._fetch_with_jina(date, top_n)
            if papers:
                logger.info(f"Successfully fetched {len(papers)} papers via Jina Reader")
                return papers
        except Exception as e:
            logger.warning(f"Jina Reader failed: {e}, falling back to direct fetch")
        
        # Fallback to direct HTML parsing
        try:
            papers = self._fetch_direct(date, top_n)
            if papers:
                logger.info(f"Successfully fetched {len(papers)} papers via direct fetch")
                return papers
        except Exception as e:
            logger.error(f"Direct fetch also failed: {e}")
            raise RuntimeError(f"Failed to fetch papers for {date}: {e}")
        
        return []
    
    def _fetch_with_jina(self, date: str, top_n: int) -> List[Paper]:
        """Fetch papers using Jina Reader API."""
        url = f"{self.HF_PAPERS_URL}?date={date}"
        jina_url = f"{self.JINA_BASE_URL}{url}"
        
        logger.info(f"Fetching via Jina: {jina_url}")
        
        response = requests.get(
            jina_url,
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout
        )
        response.raise_for_status()
        
        content = response.text
        if not content or len(content.strip()) < 100:
            raise RuntimeError("Jina Reader returned insufficient content")
        
        return self._parse_jina_content(content, top_n)
    
    def _parse_jina_content(self, content: str, top_n: int) -> List[Paper]:
        """Parse papers from Jina Reader markdown output."""
        papers = []
        
        # Jina returns markdown with paper links
        # Pattern: [Paper Title](https://huggingface.co/papers/XXXX.XXXXX)
        # Also look for upvote counts nearby
        
        lines = content.split('\n')
        current_paper = None
        
        for line in lines:
            # Look for paper links
            match = re.search(r'\[([^\]]+)\]\(https://huggingface\.co/papers/(\d{4}\.\d{4,5})\)', line)
            if match:
                title = match.group(1).strip()
                arxiv_id = match.group(2)
                
                # Skip if title looks like metadata or is too short
                if title.lower() in ['paper', 'papers', 'view', 'read']:
                    continue
                if len(title) < 5 or title.isdigit():
                    continue
                
                # Skip duplicates
                if any(p.arxiv_id == arxiv_id for p in papers):
                    continue
                
                current_paper = Paper(
                    title=title,
                    arxiv_id=arxiv_id,
                    url=f"https://huggingface.co/papers/{arxiv_id}"
                )
                papers.append(current_paper)
            
            # Look for upvote counts (usually near paper entries)
            if current_paper:
                upvote_match = re.search(r'(\d+)\s*(?:upvotes?|👍|likes?)', line, re.IGNORECASE)
                if upvote_match:
                    current_paper.upvotes = int(upvote_match.group(1))
        
        # Sort by upvotes and return top N
        papers.sort(key=lambda p: p.upvotes, reverse=True)
        return papers[:top_n]
    
    def _fetch_direct(self, date: str, top_n: int) -> List[Paper]:
        """Fetch papers by directly parsing HuggingFace HTML."""
        url = f"{self.HF_PAPERS_URL}?date={date}"
        
        logger.info(f"Fetching directly: {url}")
        
        response = requests.get(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            timeout=self.timeout
        )
        response.raise_for_status()
        
        return self._parse_html_content(response.text, top_n)
    
    def _parse_html_content(self, html: str, top_n: int) -> List[Paper]:
        """Parse papers from HuggingFace HTML page."""
        soup = BeautifulSoup(html, 'lxml')
        papers = []
        
        # HuggingFace papers page structure:
        # Each paper is in an article or div with paper link
        # Look for links to /papers/XXXX.XXXXX
        
        # Find all paper links
        paper_links = soup.find_all('a', href=re.compile(r'/papers/\d{4}\.\d{4,5}$'))
        
        seen_ids = set()
        for link in paper_links:
            href = link.get('href', '')
            match = re.search(r'/papers/(\d{4}\.\d{4,5})$', href)
            if not match:
                continue
            
            arxiv_id = match.group(1)
            if arxiv_id in seen_ids:
                continue
            seen_ids.add(arxiv_id)
            
            # Get title from link text or nearby elements
            title = self._extract_title(link)
            if not title or len(title) < 5:
                continue
            
            # Try to find upvote count
            upvotes = self._extract_upvotes(link)
            
            # Try to find thumbnail
            thumbnail = self._extract_thumbnail(link)
            
            paper = Paper(
                title=title,
                arxiv_id=arxiv_id,
                url=f"https://huggingface.co/papers/{arxiv_id}",
                upvotes=upvotes,
                thumbnail=thumbnail
            )
            papers.append(paper)
        
        # Sort by upvotes and return top N
        papers.sort(key=lambda p: p.upvotes, reverse=True)
        return papers[:top_n]
    
    def _extract_title(self, link_element) -> str:
        """Extract paper title from link element or its context."""
        # First try the link text itself
        text = link_element.get_text(strip=True)
        if text and len(text) > 10 and len(text) < 300:
            return text
        
        # Try parent elements
        parent = link_element.parent
        for _ in range(3):  # Go up to 3 levels
            if parent is None:
                break
            
            # Look for heading elements
            heading = parent.find(['h1', 'h2', 'h3', 'h4'])
            if heading:
                text = heading.get_text(strip=True)
                if text and len(text) > 10:
                    return text
            
            # Look for title class
            title_elem = parent.find(class_=re.compile(r'title', re.IGNORECASE))
            if title_elem:
                text = title_elem.get_text(strip=True)
                if text and len(text) > 10:
                    return text
            
            parent = parent.parent
        
        return ""
    
    def _extract_upvotes(self, link_element) -> int:
        """Extract upvote count from near the link element."""
        # Look in parent containers for upvote indicators
        parent = link_element.parent
        for _ in range(5):
            if parent is None:
                break
            
            text = parent.get_text()
            # Look for number followed by upvote indicators
            match = re.search(r'(\d+)\s*(?:upvotes?|👍|likes?|points?)', text, re.IGNORECASE)
            if match:
                return int(match.group(1))
            
            # Also look for standalone numbers that might be upvotes
            # (HF often shows just the number)
            upvote_elem = parent.find(class_=re.compile(r'upvote|vote|like', re.IGNORECASE))
            if upvote_elem:
                num_match = re.search(r'(\d+)', upvote_elem.get_text())
                if num_match:
                    return int(num_match.group(1))
            
            parent = parent.parent
        
        return 0
    
    def _extract_thumbnail(self, link_element) -> Optional[str]:
        """Extract thumbnail image URL from near the link element."""
        parent = link_element.parent
        for _ in range(5):
            if parent is None:
                break
            
            img = parent.find('img')
            if img:
                src = img.get('src') or img.get('data-src')
                if src and ('arxiv' in src or 'huggingface' in src or 'thumbnail' in src):
                    return src
            
            parent = parent.parent
        
        return None


def fetch_daily_papers(date: str, top_n: int = 5, user_agent: str = "SelfLetterBot/1.0") -> List[Paper]:
    """
    Convenience function to fetch daily papers.
    
    Args:
        date: Date string in YYYY-MM-DD format
        top_n: Number of top papers to return
        user_agent: User agent string for requests
    
    Returns:
        List of Paper objects
    """
    fetcher = PaperFetcher(user_agent=user_agent)
    return fetcher.fetch_daily_papers(date, top_n)
