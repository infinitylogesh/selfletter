"""
YouTube video processor with transcript support.
"""

import re
import logging
from typing import Tuple
from .base import BaseProcessor

logger = logging.getLogger(__name__)


class YouTubeProcessor(BaseProcessor):
    """Processor for YouTube videos (uses transcript if available)."""
    
    YOUTUBE_RE = re.compile(
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})"
    )
    
    def can_handle(self, url: str) -> bool:
        """Check if URL is a YouTube link."""
        return bool(self.YOUTUBE_RE.search(url))
    
    def get_content_type(self) -> str:
        """Return content type identifier."""
        return "youtube"
    
    def _extract_video_id(self, url: str) -> str:
        """Extract YouTube video ID from URL."""
        m = self.YOUTUBE_RE.search(url)
        if m:
            return m.group(1)
        return None
    
    def extract_content(self, url: str) -> Tuple[str, str, str]:
        """
        Extract content from YouTube video.
        Jina Reader can extract transcripts automatically.
        """
        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError(f"Could not extract YouTube video ID from URL: {url}")
        
        logger.info(f"Processing YouTube video: {video_id}")
        
        # Normalize URL
        normalized_url = f"https://www.youtube.com/watch?v={video_id}"
        
        try:
            # Jina Reader can extract YouTube transcripts
            content = self.fetch_with_jina(normalized_url)
            
            # Extract title from content
            title = self._extract_title_from_content(content, video_id)
            
            # Check if we got a transcript
            if "transcript" in content.lower() or len(content) > 1000:
                logger.info(f"Successfully extracted YouTube content for: {video_id}")
                return title, content, normalized_url
            else:
                logger.warning(f"Limited content extracted for YouTube video: {video_id}")
                return title, content, normalized_url
                
        except Exception as e:
            logger.error(f"Failed to extract YouTube content for {video_id}: {e}")
            raise RuntimeError(f"Failed to process YouTube video: {e}")
    
    def _extract_title_from_content(self, content: str, video_id: str) -> str:
        """Extract title from content text."""
        lines = content.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line) > 10 and len(line) < 200:
                # Skip common headers
                if not line.lower().startswith(('transcript', 'youtube', 'video')):
                    return line
        
        # Fallback to video ID
        return f"YouTube Video {video_id}"
