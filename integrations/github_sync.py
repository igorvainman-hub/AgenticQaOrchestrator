from __future__ import annotations

import os
from github import Github


class GithubSync:
    def __init__(self) -> None:
        token = os.environ["GITHUB_TOKEN"]
        self._repo = Github(token).get_repo(os.environ["GITHUB_REPO"])
        self._branch = os.environ.get("GITHUB_BRANCH", "main")

    def push_results(self, files: dict[str, str], commit_message: str) -> str:
        ref = self._repo.get_git_ref(f"heads/{self._branch}")
        base_sha = ref.object.sha
        base_tree = self._repo.get_git_tree(base_sha)

        blobs = []
        for path, content in files.items():
            blob = self._repo.create_git_blob(content, "utf-8")
            blobs.append({
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob.sha,
            })

        new_tree = self._repo.create_git_tree(blobs, base_tree)
        parent_commit = self._repo.get_git_commit(base_sha)
        new_commit = self._repo.create_git_commit(commit_message, new_tree, [parent_commit])
        ref.edit(new_commit.sha)
        return new_commit.sha