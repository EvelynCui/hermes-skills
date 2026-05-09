"""Optional email delivery for generated reports."""

from __future__ import annotations

import os
import logging
import smtplib
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = PROJECT_ROOT / "skills" / "financial-daily-briefing" / "templates" / "email_template.md"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports"


def build_email_preview(report_path: Path, executive_summary: str, output_dir: Path | None = None) -> Path:
    """Write an email preview file and return its path."""
    load_dotenv(PROJECT_ROOT / ".env")
    output_dir = output_dir or DEFAULT_REPORT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    body = (
        template.replace("{{ report_date }}", date.today().isoformat())
        .replace("{{ report_path }}", str(report_path))
        .replace("{{ executive_summary }}", executive_summary)
    )

    configured_to = os.getenv("EMAIL_TO")
    if configured_to:
        body += f"\n\nConfigured recipient: {configured_to}\n"
    body += "\nEmail sending is disabled in this MVP.\n"

    output_path = output_dir / f"email_preview_{date.today().isoformat()}.txt"
    output_path.write_text(body, encoding="utf-8")
    return output_path


def send_report_email(report_path: Path) -> bool:
    """Send the report by SMTP when email settings are complete.

    Returns True when the message is sent. Missing email settings are logged and
    return False so the daily briefing workflow can still finish.
    """
    load_dotenv(PROJECT_ROOT / ".env")
    required_settings = {
        "EMAIL_SMTP_HOST": os.getenv("EMAIL_SMTP_HOST"),
        "EMAIL_USERNAME": os.getenv("EMAIL_USERNAME"),
        "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD"),
        "EMAIL_FROM": os.getenv("EMAIL_FROM"),
        "EMAIL_TO": os.getenv("EMAIL_TO"),
    }
    missing = [name for name, value in required_settings.items() if not value]
    if missing:
        logging.warning("Email skipped. Missing settings: %s", ", ".join(missing))
        return False

    port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    message = EmailMessage()
    message["Subject"] = f"SEC Filings Briefing - {date.today().isoformat()}"
    message["From"] = required_settings["EMAIL_FROM"]
    message["To"] = required_settings["EMAIL_TO"]
    message.set_content(report_path.read_text(encoding="utf-8"))

    with smtplib.SMTP(required_settings["EMAIL_SMTP_HOST"], port, timeout=30) as server:
        server.starttls()
        server.login(required_settings["EMAIL_USERNAME"], required_settings["EMAIL_PASSWORD"])
        server.send_message(message)

    logging.info("Sent email report to %s", required_settings["EMAIL_TO"])
    return True
