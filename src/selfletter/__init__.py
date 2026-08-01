from .processors import ProcessorFactory
from .combiner import NewsletterCombiner
from .fetcher import PaperFetcher, Paper, fetch_daily_papers
from .renderer import NewsletterRenderer, render_newsletter
from .services import get_service, NewsletterService, EmailService, KitService

__version__ = "0.2.0"

__all__ = [
    'ProcessorFactory',
    'NewsletterCombiner',
    'PaperFetcher',
    'Paper',
    'fetch_daily_papers',
    'NewsletterRenderer',
    'render_newsletter',
    'get_service',
    'NewsletterService',
    'EmailService',
    'KitService',
]
