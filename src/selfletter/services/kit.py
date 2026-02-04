"""
Kit.com (formerly ConvertKit) newsletter delivery service.
Uses v3 API which requires api_secret for authentication.
"""

import os
import logging
from typing import Optional, Union
from datetime import datetime

import requests

from .base import NewsletterService

logger = logging.getLogger(__name__)


class KitService(NewsletterService):
    """Newsletter delivery via Kit.com API (v3)."""
    
    API_BASE_URL = "https://api.convertkit.com/v3"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        """
        Initialize Kit.com service.
        
        Args:
            api_key: Kit.com public API key (default: from KIT_API_KEY env)
            api_secret: Kit.com API secret (default: from KIT_API_SECRET env)
        """
        self.api_key = api_key or os.environ.get("KIT_API_KEY")
        self.api_secret = api_secret or os.environ.get("KIT_API_SECRET")
    
    @property
    def service_name(self) -> str:
        return "Kit.com"
    
    def validate_config(self) -> bool:
        """Check if all required configuration is present."""
        if not self.api_secret:
            logger.warning("Kit.com configuration incomplete. Required: KIT_API_SECRET")
            return False
        return True
    
    def _get_headers(self) -> dict:
        """Get headers for Kit.com API requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    
    def send(
        self, 
        subject: str, 
        html_content: str, 
        markdown_content: Optional[str] = None,
        send_at: Optional[Union[datetime, str]] = None
    ) -> bool:
        """
        Send newsletter via Kit.com broadcast (v3 API).
        
        Creates a broadcast (email to all subscribers) with the given content.
        Can optionally schedule the broadcast for a future time.
        
        Args:
            subject: Email subject line
            html_content: HTML formatted content
            markdown_content: Optional plain text fallback (not used by Kit)
            send_at: Optional datetime or ISO 8601 string to schedule the broadcast.
                     If None, creates a draft. If provided, schedules for that time.
                     Example: "2026-02-05T10:00:00Z" or datetime object
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.validate_config():
            logger.error("Cannot send via Kit.com: configuration is incomplete")
            return False
        
        # Convert datetime to ISO 8601 string if needed
        scheduled_time = None
        if send_at is not None:
            if isinstance(send_at, datetime):
                scheduled_time = send_at.isoformat()
            else:
                scheduled_time = send_at
        
        # Create a broadcast using v3 API
        broadcast_data = {
            "api_secret": self.api_secret,
            "subject": subject,
            "content": html_content,
        }
        
        # Add send_at parameter if scheduling is requested
        if scheduled_time:
            broadcast_data["send_at"] = scheduled_time
        
        try:
            if scheduled_time:
                logger.info(f"Creating scheduled Kit.com broadcast for {scheduled_time}: {subject}")
            else:
                logger.info(f"Creating Kit.com broadcast draft: {subject}")
            
            # Create the broadcast
            response = requests.post(
                f"{self.API_BASE_URL}/broadcasts",
                headers=self._get_headers(),
                json=broadcast_data,
                timeout=60
            )
            
            if response.status_code == 401:
                logger.error("Kit.com authentication failed. Check your API secret.")
                return False
            
            response.raise_for_status()
            result = response.json()
            
            broadcast = result.get("broadcast", {})
            broadcast_id = broadcast.get("id")
            if not broadcast_id:
                logger.error(f"Failed to create broadcast: {result}")
                return False
            
            logger.info(f"Broadcast created with ID: {broadcast_id}")
            
            if scheduled_time:
                logger.info(f"Broadcast {broadcast_id} scheduled for {scheduled_time}")
            else:
                logger.info(f"Broadcast {broadcast_id} created as draft (check dashboard to send or schedule)")
            
            return True
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Kit.com API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Kit.com request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send via Kit.com: {e}")
            return False
    
    def get_subscribers_count(self) -> Optional[int]:
        """
        Get the total number of subscribers.
        
        Returns:
            Number of subscribers or None if failed
        """
        if not self.validate_config():
            return None
        
        try:
            response = requests.get(
                f"{self.API_BASE_URL}/subscribers",
                params={"api_secret": self.api_secret, "page": 1},
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            return result.get("total_subscribers", 0)
            
        except Exception as e:
            logger.error(f"Failed to get subscriber count: {e}")
            return None
