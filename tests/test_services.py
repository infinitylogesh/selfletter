"""Tests for newsletter delivery services."""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from selfletter.services import (
    ButtondownService,
    EmailService,
    KitService,
    NewsletterService,
    get_service,
)


class TestGetService:
    """Tests for the service factory function."""

    def test_get_buttondown_service(self):
        service = get_service("buttondown")
        assert isinstance(service, ButtondownService)
    
    def test_get_email_service(self):
        service = get_service("email")
        assert isinstance(service, EmailService)
    
    def test_get_kit_service(self):
        service = get_service("kit")
        assert isinstance(service, KitService)
    
    def test_get_service_case_insensitive(self):
        service = get_service("EMAIL")
        assert isinstance(service, EmailService)
        
        service = get_service("Kit")
        assert isinstance(service, KitService)

        service = get_service("ButtonDown")
        assert isinstance(service, ButtondownService)
    
    def test_get_unknown_service(self):
        with pytest.raises(ValueError, match="Unknown service type"):
            get_service("unknown")


class TestEmailService:
    """Tests for the EmailService class."""
    
    def test_service_name(self):
        service = EmailService()
        assert service.service_name == "Email (SMTP)"
    
    @patch.dict('os.environ', {}, clear=True)
    def test_validate_config_missing(self):
        service = EmailService(smtp_user=None, smtp_pass=None, email_to=None)
        assert service.validate_config() is False
    
    def test_validate_config_complete(self):
        service = EmailService(
            smtp_user="user@test.com",
            smtp_pass="password",
            email_to="recipient@test.com"
        )
        assert service.validate_config() is True
    
    @patch('selfletter.services.email.smtplib.SMTP_SSL')
    def test_send_success(self, mock_smtp):
        """Test successful email send."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        service = EmailService(
            smtp_host="smtp.test.com",
            smtp_port=465,
            smtp_user="user@test.com",
            smtp_pass="password",
            email_to="recipient@test.com"
        )
        
        result = service.send(
            subject="Test Subject",
            html_content="<h1>Test</h1>",
            markdown_content="# Test"
        )
        
        assert result is True
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
    
    @patch('selfletter.services.email.smtplib.SMTP_SSL')
    def test_send_auth_failure(self, mock_smtp):
        """Test email send with authentication failure."""
        import smtplib
        mock_smtp.return_value.__enter__.return_value.login.side_effect = \
            smtplib.SMTPAuthenticationError(535, b"Auth failed")
        
        service = EmailService(
            smtp_user="user@test.com",
            smtp_pass="wrong",
            email_to="recipient@test.com"
        )
        
        result = service.send(
            subject="Test",
            html_content="<h1>Test</h1>"
        )
        
        assert result is False

    @patch.dict('os.environ', {}, clear=True)
    def test_send_without_config(self):
        """Test send fails gracefully without config."""
        service = EmailService(smtp_user=None, smtp_pass=None, email_to=None)

        result = service.send(
            subject="Test",
            html_content="<h1>Test</h1>"
        )

        assert result is False


class TestButtondownService:
    def test_service_name(self):
        assert ButtondownService(api_key="test_key").service_name == "Buttondown"

    @patch.dict('os.environ', {}, clear=True)
    def test_validate_config_missing(self):
        assert ButtondownService(api_key=None).validate_config() is False

    def test_validate_config_rejects_unknown_status(self):
        service = ButtondownService(api_key="test_key", status="send_now")
        assert service.validate_config() is False

    @patch('selfletter.services.buttondown.requests.post')
    def test_create_draft_with_markdown_and_idempotency_key(self, mock_post):
        response = MagicMock()
        response.json.return_value = {"id": "em_123", "status": "draft"}
        response.raise_for_status = MagicMock()
        mock_post.return_value = response

        service = ButtondownService(api_key="test_key", status="draft")
        assert service.send(
            subject="Daily AI Papers - 2026-08-01",
            html_content="<h1>Fallback</h1>",
            markdown_content="# Daily issue",
        ) is True

        request = mock_post.call_args
        assert request.kwargs["json"]["body"] == "# Daily issue"
        assert request.kwargs["json"]["status"] == "draft"
        assert request.kwargs["json"]["slug"] == "daily-ai-papers-2026-08-01"
        assert request.kwargs["headers"]["X-Idempotency-Key"]

    @patch('selfletter.services.buttondown.requests.post')
    def test_schedule_email(self, mock_post):
        response = MagicMock()
        response.json.return_value = {"id": "em_123", "status": "scheduled"}
        response.raise_for_status = MagicMock()
        mock_post.return_value = response

        service = ButtondownService(api_key="test_key")
        send_at = datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc)
        assert service.send("Subject", "<p>Body</p>", send_at=send_at) is True

        payload = mock_post.call_args.kwargs["json"]
        assert payload["status"] == "scheduled"
        assert payload["publish_date"] == "2026-08-02T08:00:00+00:00"

    def test_scheduled_status_requires_send_time(self):
        service = ButtondownService(api_key="test_key", status="scheduled")
        assert service.send("Subject", "<p>Body</p>") is False


class TestKitService:
    """Tests for the KitService class."""
    
    def test_service_name(self):
        service = KitService()
        assert service.service_name == "Kit.com"
    
    def test_validate_config_missing(self):
        service = KitService(api_secret=None)
        assert service.validate_config() is False
    
    def test_validate_config_complete(self):
        service = KitService(api_secret="test_secret")
        assert service.validate_config() is True
    
    def test_get_headers(self):
        service = KitService(api_secret="test_secret")
        headers = service._get_headers()
        
        assert headers["Content-Type"] == "application/json"
    
    @patch('selfletter.services.kit.requests.post')
    def test_send_success(self, mock_post):
        """Test successful Kit.com send."""
        # Mock create broadcast response
        create_response = MagicMock()
        create_response.status_code = 200
        create_response.json.return_value = {"broadcast": {"id": "123"}}
        create_response.raise_for_status = MagicMock()
        
        mock_post.return_value = create_response

        service = KitService(api_secret="test_secret")
        
        result = service.send(
            subject="Test Subject",
            html_content="<h1>Test</h1>"
        )
        
        assert result is True
        assert mock_post.call_count == 1
    
    @patch('selfletter.services.kit.requests.post')
    def test_send_auth_failure(self, mock_post):
        """Test Kit.com send with authentication failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        service = KitService(api_secret="invalid_secret")
        
        result = service.send(
            subject="Test",
            html_content="<h1>Test</h1>"
        )
        
        assert result is False
    
    def test_send_without_config(self):
        """Test send fails gracefully without config."""
        service = KitService(api_secret=None)
        
        result = service.send(
            subject="Test",
            html_content="<h1>Test</h1>"
        )
        
        assert result is False
    
    @patch('selfletter.services.kit.requests.get')
    def test_get_subscribers_count(self, mock_get):
        """Test getting subscriber count."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"total_subscribers": 100}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        service = KitService(api_secret="test_secret")
        count = service.get_subscribers_count()
        
        assert count == 100
    
    @patch('selfletter.services.kit.requests.get')
    def test_get_subscribers_count_failure(self, mock_get):
        """Test subscriber count with API failure."""
        mock_get.side_effect = Exception("API error")
        
        service = KitService(api_secret="test_secret")
        count = service.get_subscribers_count()
        
        assert count is None
