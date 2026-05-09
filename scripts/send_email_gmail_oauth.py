"""Send a Markdown report with Gmail API OAuth 2.0.

This script does not use SMTP passwords or app passwords. It uses:

- credentials.json: OAuth client secret downloaded from Google Cloud.
- token.json: local OAuth token cache created after the first consent flow.
"""

from __future__ import annotations

import argparse
import base64
import logging
import os
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SKILL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path.cwd()
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
DEFAULT_CREDENTIALS_PATH = SKILL_ROOT / "credentials.json"
DEFAULT_TOKEN_PATH = SKILL_ROOT / "token.json"


def load_gmail_credentials(
    credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> Credentials:
    """Load, refresh, or create Gmail OAuth credentials."""
    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), [GMAIL_SEND_SCOPE])

    if creds and creds.expired and creds.refresh_token:
        logging.info("Refreshing Gmail OAuth token")
        creds.refresh(Request())

    if not creds or not creds.valid:
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"Missing {credentials_path}. Download an OAuth client secret from Google Cloud first."
            )
        logging.info("Starting Gmail OAuth browser consent flow")
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), [GMAIL_SEND_SCOPE])
        creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def create_message(sender: str, recipient: str, subject: str, body: str) -> dict[str, str]:
    """Create a Gmail API message payload."""
    message = EmailMessage()
    message["To"] = recipient
    message["From"] = sender
    message["Subject"] = subject
    message.set_content(body)
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": encoded_message}


def send_report_via_gmail_oauth(
    report_path: Path,
    recipient: str,
    sender: str = "me",
    subject: str = "Daily Financial Briefing",
    credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> bool:
    """Read a Markdown report and send it with the Gmail API."""
    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")

    creds = load_gmail_credentials(credentials_path=credentials_path, token_path=token_path)
    service = build("gmail", "v1", credentials=creds)
    body = report_path.read_text(encoding="utf-8")
    message = create_message(sender=sender, recipient=recipient, subject=subject, body=body)
    service.users().messages().send(userId="me", body=message).execute()
    logging.info("Sent Gmail API report to %s", recipient)
    return True


def send_report_email(report_path: Path) -> bool:
    """Environment-driven wrapper used by the briefing runner."""
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(SKILL_ROOT / ".env")
    recipient = os.getenv("EMAIL_TO", "").strip()
    if not recipient:
        logging.warning("Email skipped. EMAIL_TO is missing.")
        return False

    sender = os.getenv("EMAIL_FROM", "me").strip() or "me"
    subject = os.getenv("EMAIL_SUBJECT", "Daily Financial Briefing").strip()
    credentials_path = Path(os.getenv("GMAIL_CREDENTIALS_PATH", str(DEFAULT_CREDENTIALS_PATH)))
    token_path = Path(os.getenv("GMAIL_TOKEN_PATH", str(DEFAULT_TOKEN_PATH)))

    if not credentials_path.is_absolute():
        credentials_path = PROJECT_ROOT / credentials_path
    if not token_path.is_absolute():
        token_path = PROJECT_ROOT / token_path

    return send_report_via_gmail_oauth(
        report_path=report_path,
        recipient=recipient,
        sender=sender,
        subject=subject,
        credentials_path=credentials_path,
        token_path=token_path,
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for explicitly requested email sends."""
    parser = argparse.ArgumentParser(description="Send a Markdown report with Gmail OAuth.")
    parser.add_argument("report_path", type=Path, help="Path to the Markdown report to send.")
    parser.add_argument("--to", default=os.getenv("EMAIL_TO"), help="Recipient email address.")
    parser.add_argument("--from-email", default=os.getenv("EMAIL_FROM", "me"), help="Sender email or 'me'.")
    parser.add_argument("--subject", default=os.getenv("EMAIL_SUBJECT", "Daily Financial Briefing"))
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(SKILL_ROOT / ".env")
    args = parse_args()
    if not args.to:
        raise SystemExit("EMAIL_TO or --to is required.")
    send_report_via_gmail_oauth(
        report_path=args.report_path,
        recipient=args.to,
        sender=args.from_email,
        subject=args.subject,
    )
