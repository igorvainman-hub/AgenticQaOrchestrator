from __future__ import annotations

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]


class GoogleDocsClient:
    def __init__(self, service_account_path: str) -> None:
        creds = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=SCOPES
        )
        self._service = build("docs", "v1", credentials=creds)

    def get_document_text(self, doc_id: str) -> str:
        doc = self._service.documents().get(documentId=doc_id).execute()
        content = doc.get("body", {}).get("content", [])
        text_parts: list[str] = []
        for block in content:
            paragraph = block.get("paragraph")
            if not paragraph:
                continue
            for element in paragraph.get("elements", []):
                text_run = element.get("textRun")
                if text_run:
                    text_parts.append(text_run.get("content", ""))
        return "".join(text_parts)