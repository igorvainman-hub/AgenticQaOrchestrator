from __future__ import annotations

import sys
import pytest
from unittest.mock import MagicMock, patch


def test_no_file_found_exits_0(monkeypatch):
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./creds.json")
    monkeypatch.setenv("GOOGLE_DRIVE_INPUT_FOLDER_ID", "folder1")
    monkeypatch.setenv("GOOGLE_DRIVE_PROCESSED_FOLDER_ID", "folder2")

    mock_drive = MagicMock()
    mock_drive.find_new_feature_file.return_value = None

    with patch("integrations.google_drive.GoogleDriveClient", return_value=mock_drive):
        with pytest.raises(SystemExit) as exc:
            import poll_and_run
            poll_and_run.main()
        assert exc.value.code == 0


def test_empty_file_exits_1(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./creds.json")
    monkeypatch.setenv("GOOGLE_DRIVE_INPUT_FOLDER_ID", "folder1")
    monkeypatch.setenv("GOOGLE_DRIVE_PROCESSED_FOLDER_ID", "folder2")
    monkeypatch.chdir(tmp_path)

    mock_drive = MagicMock()
    mock_drive.find_new_feature_file.return_value = {"id": "fid", "name": "new_feature.txt"}
    mock_drive.download_file.return_value = "   "

    with patch("integrations.google_drive.GoogleDriveClient", return_value=mock_drive):
        with pytest.raises(SystemExit) as exc:
            import importlib
            import poll_and_run
            importlib.reload(poll_and_run)
            poll_and_run.main()
        assert exc.value.code == 1


def test_move_before_orchestrator(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./creds.json")
    monkeypatch.setenv("GOOGLE_DRIVE_INPUT_FOLDER_ID", "folder1")
    monkeypatch.setenv("GOOGLE_DRIVE_PROCESSED_FOLDER_ID", "folder2")
    monkeypatch.chdir(tmp_path)

    call_order = []
    mock_drive = MagicMock()
    mock_drive.find_new_feature_file.return_value = {"id": "fid", "name": "new_feature.txt"}
    mock_drive.download_file.return_value = "Base URL: https://example.com"
    mock_drive.move_to_processed.side_effect = lambda *a, **k: call_order.append("move")

    def fake_orchestrator(*a, **k):
        call_order.append("orchestrator")

    with patch("integrations.google_drive.GoogleDriveClient", return_value=mock_drive):
        with patch("orchestrator.main", side_effect=fake_orchestrator):
            import importlib
            import poll_and_run
            importlib.reload(poll_and_run)
            poll_and_run.main()

    assert call_order.index("move") < call_order.index("orchestrator")