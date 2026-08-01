"""
Base class for newsletter delivery services.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class NewsletterService(ABC):
    """Abstract base class for newsletter delivery services."""
    
    @abstractmethod
    def send(
        self, 
        subject: str, 
        html_content: str, 
        markdown_content: Optional[str] = None,
        send_at: Optional[Union[datetime, str]] = None
    ) -> bool:
        """
        Send the newsletter.
        
        Args:
            subject: Email/newsletter subject line
            html_content: HTML formatted content
            markdown_content: Optional plain text/markdown fallback
            send_at: Optional datetime or ISO 8601 string to schedule sending.
                     Not all services support scheduling. Default is immediate/draft.
        
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate that the service is properly configured.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def service_name(self) -> str:
        """Return the name of the service."""
        pass
