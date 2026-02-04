"""
Email (SMTP) newsletter delivery service.
"""

import os
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional, Union
from datetime import datetime

from .base import NewsletterService

logger = logging.getLogger(__name__)


class EmailService(NewsletterService):
    """Newsletter delivery via SMTP email."""
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_pass: Optional[str] = None,
        email_to: Optional[str] = None,
        email_from: Optional[str] = None,
    ):
        """
        Initialize email service.
        
        Args:
            smtp_host: SMTP server hostname (default: from SMTP_HOST env)
            smtp_port: SMTP server port (default: from SMTP_PORT env)
            smtp_user: SMTP username (default: from SMTP_USER env)
            smtp_pass: SMTP password (default: from SMTP_PASS env)
            email_to: Recipient email (default: from EMAIL_TO env)
            email_from: Sender email (default: from EMAIL_FROM env or smtp_user)
        """
        self.smtp_host = smtp_host or os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", "465"))
        self.smtp_user = smtp_user or os.environ.get("SMTP_USER")
        self.smtp_pass = smtp_pass or os.environ.get("SMTP_PASS")
        self.email_to = email_to or os.environ.get("EMAIL_TO")
        self.email_from = email_from or os.environ.get("EMAIL_FROM", self.smtp_user)
    
    @property
    def service_name(self) -> str:
        return "Email (SMTP)"
    
    def validate_config(self) -> bool:
        """Check if all required configuration is present."""
        required = [self.smtp_user, self.smtp_pass, self.email_to]
        if not all(required):
            logger.warning(
                "Email configuration incomplete. Required: SMTP_USER, SMTP_PASS, EMAIL_TO"
            )
            return False
        return True
    
    def send(
        self, 
        subject: str, 
        html_content: str, 
        markdown_content: Optional[str] = None,
        send_at: Optional[Union[datetime, str]] = None
    ) -> bool:
        """
        Send newsletter via SMTP email.
        
        Note: SMTP does not support scheduling. Emails are sent immediately.
        If send_at is provided, it will be ignored with a warning.
        
        Args:
            subject: Email subject line
            html_content: HTML formatted content
            markdown_content: Optional plain text fallback
            send_at: Ignored - SMTP sends immediately
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.validate_config():
            logger.error("Cannot send email: configuration is incomplete")
            return False
        
        if send_at is not None:
            logger.warning("SMTP email service does not support scheduling. Sending immediately.")
        
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = self.email_to
        
        # Set plain text version as fallback
        if markdown_content:
            msg.set_content(markdown_content)
        else:
            msg.set_content("Please view this email in an HTML-capable email client.")
        
        # Add HTML version
        msg.add_alternative(html_content, subtype="html")
        
        try:
            logger.info(f"Sending email to {self.email_to} via {self.smtp_host}:{self.smtp_port}")
            
            # Use SSL on port 465
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {self.email_to}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
