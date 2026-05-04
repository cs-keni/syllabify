"""
Email delivery. Uses SMTP (any provider). Set SMTP_* env vars to enable.
Compatible with Gmail App Passwords, Resend SMTP, SendGrid SMTP, etc.
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER"))


def send_email(to: str, subject: str, html: str, text: str | None = None) -> bool:
    """Send an email. Returns True on success, False if unconfigured or on error."""
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")
    from_addr = os.getenv("SMTP_FROM", user) or user

    if not host or not user:
        logger.debug("Email skipped: SMTP_HOST/SMTP_USER not configured")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to

    if text:
        msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.ehlo()
            if port != 465:
                smtp.starttls()
            if password:
                smtp.login(user, password)
            smtp.sendmail(from_addr, [to], msg.as_string())
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False
