from __future__ import annotations

import os
import pytest
from unittest.mock import MagicMock, patch


def test_push_results_returns_sha(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "owner/repo")
    monkeypatch.setenv("GITHUB_BRANCH", "main")

    mock_repo = MagicMock()
    mock_ref = MagicMock()
    mock_ref.object.sha = "abc123"
    mock_repo.get_git_ref.return_value = mock_ref
    mock_repo.get_git_tree.return_value = MagicMock()
    mock_blob = MagicMock()
    mock_blob.sha = "blobsha"
    mock_repo.create_git_blob.return_value = mock_blob
    mock_repo.create_git_tree.return_value = MagicMock()
    mock_commit = MagicMock()
    mock_commit.sha = "newsha123"
    mock_repo.create_git_commit.return_value = mock_commit
    mock_repo.get_git_commit.return_value = MagicMock()

    with patch("integrations.github_sync.Github") as mock_github:
        mock_github.return_value.get_repo.return_value = mock_repo
        from integrations.github_sync import GithubSync
        sync = GithubSync()
        sha = sync.push_results({"results/test.md": "content"}, "test commit")

    assert sha == "newsha123"
    assert len(sha) > 0