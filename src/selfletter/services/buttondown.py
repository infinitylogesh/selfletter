"""Buttondown newsletter delivery service."""

import hashlib
import logging
import os
import re
from datetime import datetime
from typing import Optional, Union

import requests

from .base import NewsletterService

logger = logging.getLogger(__name__)


class ButtondownService(NewsletterService):
    """Create or update draft, scheduled, or queued Buttondown emails."""

    API_URL = "https://api.buttondown.com/v1/emails"
    VALID_STATUSES = {"draft", "scheduled", "about_to_send"}

    def __init__(
        self,
        api_key: Optional[str] = None,
        status: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("BUTTONDOWN_API_KEY")
        self.status = (status or os.environ.get("BUTTONDOWN_STATUS", "draft")).lower()

    @property
    def service_name(self) -> str:
        return "Buttondown"

    def validate_config(self) -> bool:
        if not self.api_key:
            logger.warning("Buttondown configuration incomplete. Required: BUTTONDOWN_API_KEY")
            return False
        if self.status not in self.VALID_STATUSES:
            logger.warning(
                "Invalid BUTTONDOWN_STATUS=%s. Supported values: %s",
                self.status,
                sorted(self.VALID_STATUSES),
            )
            return False
        return True

    @staticmethod
    def _slugify(subject: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")
        return slug[:100] or "selfletter"

    @staticmethod
    def _format_datetime(value: Union[datetime, str]) -> str:
        return value.isoformat() if isinstance(value, datetime) else value

    def _headers(self, idempotency_key: Optional[str] = None) -> dict:
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        return headers

    def _find_existing_email(self, subject: str, slug: str) -> Optional[dict]:
        """Find a draft or scheduled issue that can safely be updated."""
        response = requests.get(
            self.API_URL,
            headers=self._headers(),
            params={
                "subject": subject,
                "status": ["draft", "scheduled"],
            },
            timeout=30,
        )
        response.raise_for_status()
        for email in response.json().get("results", []):
            if email.get("subject") == subject and email.get("slug") == slug:
                return email
        return None

    def send(
        self,
        subject: str,
        html_content: str,
        markdown_content: Optional[str] = None,
        send_at: Optional[Union[datetime, str]] = None,
    ) -> bool:
        """Create a new issue or update the existing draft for the same subject."""
        if not self.validate_config():
            logger.error("Cannot publish to Buttondown: configuration is incomplete")
            return False

        status = "scheduled" if send_at is not None else self.status
        if status == "scheduled" and send_at is None:
            logger.error("BUTTONDOWN_STATUS=scheduled requires SCHEDULE_MINUTES to be greater than 0")
            return False

        body = markdown_content or html_content
        slug = self._slugify(subject)
        issue_key = hashlib.sha256(f"selfletter:{subject}".encode("utf-8")).hexdigest()
        content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        request_key = hashlib.sha256(
            f"{issue_key}:{content_hash}:{status}".encode("utf-8")
        ).hexdigest()

        payload = {
            "subject": subject,
            "body": body,
            "status": status,
            "email_type": "public",
            "archival_mode": "enabled",
            "slug": slug,
            "description": "A five-minute briefing on the AI papers that matter.",
            "metadata": {
                "source": "selfletter",
                "issue_key": issue_key,
                "content_hash": content_hash,
            },
        }
        if send_at is not None:
            payload["publish_date"] = self._format_datetime(send_at)

        try:
            existing = self._find_existing_email(subject, slug)
            if existing:
                response = requests.patch(
                    f"{self.API_URL}/{existing['id']}",
                    headers=self._headers(),
                    json=payload,
                    timeout=60,
                )
                operation = "updated"
            else:
                response = requests.post(
                    self.API_URL,
                    headers=self._headers(request_key),
                    json=payload,
                    timeout=60,
                )
                operation = "created"

            response.raise_for_status()
            email = response.json()
            logger.info(
                "Buttondown issue %s: id=%s status=%s url=%s",
                operation,
                email.get("id", existing.get("id") if existing else "unknown"),
                email.get("status", status),
                email.get("absolute_url", "not published yet"),
            )
            return True
        except requests.exceptions.HTTPError as exc:
            logger.error("Buttondown API error: %s", exc)
            if exc.response is not None:
                logger.error("Buttondown response: %s", exc.response.text)
            return False
        except requests.exceptions.RequestException as exc:
            logger.error("Buttondown request failed: %s", exc)
            return False

