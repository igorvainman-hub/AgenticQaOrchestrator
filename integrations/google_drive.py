from __future__ import annotations

import io
import os
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


class GoogleDriveClient:
    def __init__(self, service_account_path: str) -> None:
        creds = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=SCOPES
        )
        self._service = build("drive", "v3", credentials=creds)

    def find_new_feature_file(self, folder_id: str) -> dict | None:
        today = datetime.now(timezone.utc).date().isoformat()
        q = (
            f"'{folder_id}' in parents and name = 'new_feature.txt' "
            f"and trashed = false"
        )
        result = (
            self._service.files()
            .list(q=q, fields="files(id, name, createdTime)")
            .execute()
        )
        for f in result.get("files", []):
            created_date = f["createdTime"][:10]
            if created_date == today:
                return f
        return None

    def download_file(self, file_id: str) -> str:
        request = self._service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf.getvalue().decode("utf-8")

    def move_to_processed(
        self, file_id: str, input_folder_id: str, processed_folder_id: str
    ) -> None:
        self._service.files().update(
            fileId=file_id,
            addParents=processed_folder_id,
            removeParents=input_folder_id,
            fields="id",
        ).execute()

    def upload_file(self, local_path: str, folder_id: str, mime_type: str = "application/octet-stream") -> str:
        from googleapiclient.http import MediaFileUpload
        import os
        file_metadata = {"name": os.path.basename(local_path), "parents": [folder_id]}
        media = MediaFileUpload(local_path, mimetype=mime_type)
        f = self._service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        return f["id"]

    def get_or_create_subfolder(self, parent_id: str, name: str) -> str:
        q = f"'{parent_id}' in parents and name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        result = self._service.files().list(q=q, fields="files(id)").execute()
        files = result.get("files", [])
        if files:
            return files[0]["id"]
        folder = self._service.files().create(
            body={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]},
            fields="id",
        ).execute()
        return folder["id"]