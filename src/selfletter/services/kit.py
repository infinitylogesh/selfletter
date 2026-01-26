"""
Kit.com (formerly ConvertKit) newsletter delivery service.
"""

import os
import logging
import json
from typing import Optional

import requests

from .base import NewsletterService

logger = logging.getLogger(__name__)


class KitService(NewsletterService):
    """Newsletter delivery via Kit.com API."""
    
    API_BASE_URL = "https://api.kit.com/v4"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        """
        Initialize Kit.com service.
        
        Args:
            api_key: Kit.com API key (default: from KIT_API_KEY env)
            api_secret: Kit.com API secret (default: from KIT_API_SECRET env)
        """
        self.api_key = api_key or os.environ.get("KIT_API_KEY")
        self.api_secret = api_secret or os.environ.get("KIT_API_SECRET")
    
    @property
    def service_name(self) -> str:
        return "Kit.com"
    
    def validate_config(self) -> bool:
        """Check if all required configuration is present."""
        if not self.api_key:
            logger.warning("Kit.com configuration incomplete. Required: KIT_API_KEY")
            return False
        return True
    
    def _get_headers(self) -> dict:
        """Get headers for Kit.com API requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        # Kit.com uses API key in Authorization header
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    def send(self, subject: str, html_content: str, markdown_content: Optional[str] = None) -> bool:
        """
        Send newsletter via Kit.com broadcast.
        
        Creates a broadcast (email to all subscribers) with the given content.
        
        Args:
            subject: Email subject line
            html_content: HTML formatted content
            markdown_content: Optional plain text fallback (not used by Kit)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.validate_config():
            logger.error("Cannot send via Kit.com: configuration is incomplete")
            return False
        
        # Create a broadcast
        broadcast_data = {
            "broadcast": {
                "subject": subject,
                "content": html_content,
                "email_layout_template": "text",  # Use raw HTML
                "public": False,
            }
        }
        
        try:
            logger.info(f"Creating Kit.com broadcast: {subject}")
            
            # Create the broadcast
            response = requests.post(
                f"{self.API_BASE_URL}/broadcasts",
                headers=self._get_headers(),
                data=json.dumps(broadcast_data),
                timeout=60
            )
            
            if response.status_code == 401:
                logger.error("Kit.com authentication failed. Check your API key.")
                return False
            
            response.raise_for_status()
            result = response.json()
            
            broadcast_id = result.get("broadcast", {}).get("id")
            if not broadcast_id:
                logger.error(f"Failed to create broadcast: {result}")
                return False
            
            logger.info(f"Broadcast created with ID: {broadcast_id}")
            
            # Send the broadcast immediately
            send_response = requests.post(
                f"{self.API_BASE_URL}/broadcasts/{broadcast_id}/send",
                headers=self._get_headers(),
                timeout=60
            )
            
            if send_response.status_code == 401:
                logger.error("Kit.com authentication failed during send.")
                return False
            
            send_response.raise_for_status()
            
            logger.info(f"Broadcast {broadcast_id} sent successfully via Kit.com")
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
                headers=self._get_headers(),
                params={"page": 1, "per_page": 1},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            return result.get("total_subscribers", 0)
            
        except Exception as e:
            logger.error(f"Failed to get subscriber count: {e}")
            return None
