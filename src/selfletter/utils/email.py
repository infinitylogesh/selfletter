import os
import logging
import smtplib
import markdown
from email.message import EmailMessage

logger = logging.getLogger(__name__)

def send_email(subject: str, body_markdown: str):
    """Send summary via email using SMTP (rendered HTML)."""
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    email_to = os.environ.get("EMAIL_TO")
    email_from = os.environ.get("EMAIL_FROM", user)

    if not all([user, password, email_to]):
        logger.warning("Email configuration missing (SMTP_USER, SMTP_PASS, EMAIL_TO). Skipping email.")
        return

    # Convert Markdown to HTML
    html_content = markdown.markdown(body_markdown)
    
    # Add some basic styling for better email rendering
    styled_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #1a1a1a; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            h2 {{ color: #2c3e50; margin-top: 30px; border-bottom: 1px solid #eee; }}
            h3 {{ color: #34495e; margin-top: 20px; }}
            a {{ color: #3498db; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            code {{ background-color: #f8f8f8; padding: 2px 4px; border-radius: 4px; font-family: monospace; }}
            hr {{ border: 0; border-top: 1px solid #eee; margin: 30px 0; }}
            blockquote {{ border-left: 4px solid #eee; padding-left: 15px; color: #666; font-style: italic; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to
    
    # Set the plain text version as a fallback
    msg.set_content(body_markdown)
    
    # Add the HTML version
    msg.add_alternative(styled_html, subtype="html")

    try:
        # SSL on 465 (simple + reliable)
        with smtplib.SMTP_SSL(host, port) as server:
            server.login(user, password)
            server.send_message(msg)
        logger.info(f"Email sent successfully to {email_to}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

