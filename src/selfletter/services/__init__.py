"""
Newsletter delivery services.
Supports multiple backends: Email (SMTP), Kit.com, etc.
"""

from .base import NewsletterService
from .buttondown import ButtondownService
from .email import EmailService
from .kit import KitService

__all__ = [
    'NewsletterService',
    'ButtondownService',
    'EmailService',
    'KitService',
    'get_service',
]


def get_service(service_type: str = "email", **kwargs) -> NewsletterService:
    """
    Factory function to get the appropriate newsletter service.
    
    Args:
        service_type: Type of service ("email", "kit")
        **kwargs: Service-specific configuration
    
    Returns:
        NewsletterService instance
    
    Raises:
        ValueError: If service_type is not supported
    """
    services = {
        "buttondown": ButtondownService,
        "email": EmailService,
        "kit": KitService,
    }
    
    service_class = services.get(service_type.lower())
    if service_class is None:
        raise ValueError(f"Unknown service type: {service_type}. Supported: {list(services.keys())}")
    
    return service_class(**kwargs)
