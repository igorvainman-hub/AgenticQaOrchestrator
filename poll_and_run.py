from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def log(msg: str) -> None:
    from datetime import datetime, timezone
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def ensure_env(var: str) -> str:
    val = os.getenv(var)
    if not val:
        raise RuntimeError(f"Missing required env var: {var}")
    return val


def main() -> None:
    service_account_json = ensure_env("GOOGLE_SERVICE_ACCOUNT_JSON")
    input_folder_id = ensure_env("GOOGLE_DRIVE_INPUT_FOLDER_ID")
    processed_folder_id = ensure_env("GOOGLE_DRIVE_PROCESSED_FOLDER_ID")

    from integrations.google_drive import GoogleDriveClient
    drive = GoogleDriveClient(service_account_json)

    log("Checking Google Drive for new feature file...")
    file_meta = drive.find_new_feature_file(input_folder_id)

    if file_meta is None:
        log("No new feature file found today. Exiting.")
        sys.exit(0)

    log(f"Found: {file_meta['name']} (id={file_meta['id']})")
    feature_text = drive.download_file(file_meta["id"])

    if not feature_text.strip():
        log("File is empty. Skipping.")
        sys.exit(1)

    Path("new_feature.txt").write_text(feature_text, encoding="utf-8")
    log("Feature file written locally.")

    drive.move_to_processed(file_meta["id"], input_folder_id, processed_folder_id)
    log("File moved to processed folder.")

    log("Starting orchestrator...")
    from orchestrator import main as run_orchestrator
    run_orchestrator(file_override="new_feature.txt")


if __name__ == "__main__":
    main()