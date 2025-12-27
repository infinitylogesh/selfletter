"""
Base content processor with Jina Reader API integration.
"""

import logging
import json
import requests
from typing import Optional, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    """Base class for all content processors."""
    
    def __init__(self, openai_api_key: str, openai_model: str, openai_endpoint: str, 
                 summary_prompt: str, max_chars: int = 200000, user_agent: str = "SelfLetterBot/1.0"):
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self.openai_endpoint = openai_endpoint
        self.summary_prompt = summary_prompt
        self.max_chars = max_chars
        self.user_agent = user_agent
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this processor can handle the given URL."""
        pass
    
    @abstractmethod
    def get_content_type(self) -> str:
        """Return the content type identifier (e.g., 'arxiv', 'blog', 'youtube')."""
        pass
    
    @abstractmethod
    def extract_content(self, url: str) -> Tuple[str, str, str]:
        """
        Extract content from URL.
        Returns: (title, content_text, actual_url_used)
        """
        pass
    
    def fetch_with_jina(self, url: str) -> str:
        """Fetch content using Jina Reader API."""
        jina_url = f"https://r.jina.ai/{url}"
        logger.info(f"Fetching content via Jina Reader: {url}")
        
        try:
            response = requests.get(
                jina_url,
                headers={"User-Agent": self.user_agent},
                timeout=60
            )
            response.raise_for_status()
            content = response.text
            
            if not content or len(content.strip()) < 100:
                raise RuntimeError(f"Jina Reader returned insufficient content ({len(content)} chars)")
            
            logger.info(f"Successfully fetched {len(content)} chars via Jina Reader")
            return content
            
        except Exception as e:
            logger.error(f"Jina Reader failed for {url}: {e}")
            raise RuntimeError(f"Failed to fetch content via Jina Reader: {e}")
    
    def summarize(self, title: str, url: str, content: str) -> str:
        """Generate summary using OpenAI API."""
        logger.info(f"Generating summary for: {title or url}")
        
        # Truncate content to stay within limits
        content = content[:self.max_chars]
        logger.info(f"Content length after truncation: {len(content)} chars")
        
        prompt = self.summary_prompt.format(
            title=title or "(untitled)", 
            url=url, 
            content=content
        )
        
        payload = {
            "model": self.openai_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 16384,
            "temperature": 0.7,
        }
        
        try:
            r = requests.post(
                self.openai_endpoint,
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps(payload),
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
            
            choices = data.get("choices", [])
            if choices:
                summary = choices[0].get("message", {}).get("content", "")
                return summary.strip() if summary else "(empty summary)"
            return "(empty summary)"
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API request failed: {e}")
    
    def process(self, url: str, title: Optional[str] = None) -> Tuple[str, str, str, str]:
        """
        Main processing method.
        Returns: (title, content_type, actual_url, summary)
        """
        extracted_title, content, actual_url = self.extract_content(url)
        final_title = title or extracted_title or actual_url
        
        summary = self.summarize(final_title, actual_url, content)
        content_type = self.get_content_type()
        
        return final_title, content_type, actual_url, summary
