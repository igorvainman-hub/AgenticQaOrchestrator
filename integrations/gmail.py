from __future__ import annotations

import base64
import os
from email.mime.text import MIMEText

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GmailClient:
    def __init__(self, service_account_path: str, sender: str) -> None:
        creds = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=SCOPES
        ).with_subject(sender)
        self._service = build("gmail", "v1", credentials=creds)
        self._sender = sender

    def send(self, to: str, subject: str, body: str) -> None:
        message = MIMEText(body)
        message["to"] = to
        message["from"] = self._sender
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        self._service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()