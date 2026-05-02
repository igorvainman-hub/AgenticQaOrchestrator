from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

REQUIRED_ENV_VARS = [
    "GITHUB_TOKEN", "GITHUB_REPO",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "GOOGLE_DRIVE_OUTPUT_FOLDER_ID",
    "GMAIL_SENDER", "GMAIL_RECIPIENT",
]


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def _validate_env() -> None:
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {missing}")


def _parse_args(file_override: str | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=file_override)
    parser.add_argument("--doc-id")
    parser.add_argument("--dry-run-llm", action="store_true")
    args, _ = parser.parse_known_args()
    if file_override and not args.file:
        args.file = file_override
    return args


def _read_feature(args: argparse.Namespace) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.doc_id:
        sa_path = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
        from integrations.google_docs import GoogleDocsClient
        return GoogleDocsClient(sa_path).get_document_text(args.doc_id)
    raise RuntimeError("Provide --file or --doc-id")


def main(file_override: str | None = None) -> None:
    load_dotenv()
    args = _parse_args(file_override)
    provider = os.getenv("LLM_PROVIDER", "openai")

    from agents.inspector import InspectorAgent
    from agents.analyzer import AnalyzerAgent
    from agents.test_writer import TestWriterAgent
    from agents.playwright_gen import PlaywrightGeneratorAgent

    if args.dry_run_llm:
        if not args.file:
            log("--dry-run-llm requires --file")
            sys.exit(1)
        feature_text = _read_feature(args)

        log("Running InspectorAgent...")
        inspector_result = InspectorAgent(provider).run(feature_text)
        log("Running AnalyzerAgent...")
        scenarios = AnalyzerAgent(provider).run(feature_text)
        log("Running TestWriterAgent...")
        test_cases_md = TestWriterAgent(provider).run(scenarios)
        log("Running PlaywrightGeneratorAgent...")
        playwright_spec = PlaywrightGeneratorAgent(provider).run({
            "scenarios": scenarios,
            "selector_hints": inspector_result.selector_hints,
        })

        Path("results").mkdir(exist_ok=True)
        Path("results/scenarios.json").write_text(json.dumps(scenarios, indent=2), encoding="utf-8")
        Path("results/test_cases.md").write_text(test_cases_md, encoding="utf-8")
        Path("results/playwright.spec.ts").write_text(playwright_spec, encoding="utf-8")
        Path("results/feature_snapshot.txt").write_text(feature_text, encoding="utf-8")
        summary = {
            "mode": "dry_run_llm",
            "scenarios_count": len(scenarios.get("scenarios", [])),
            "selector_hints_count": len(inspector_result.selector_hints.get("selectors", [])),
        }
        Path("results/dry_run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        log("Dry run complete. Results written to results/")
        return

    _validate_env()
    feature_text = _read_feature(args)
    sa_path = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

    log("Running InspectorAgent...")
    inspector_result = InspectorAgent(provider).run(feature_text)
    log("Running AnalyzerAgent...")
    scenarios = AnalyzerAgent(provider).run(feature_text)
    log("Running TestWriterAgent...")
    test_cases_md = TestWriterAgent(provider).run(scenarios)
    log("Running PlaywrightGeneratorAgent...")
    playwright_spec = PlaywrightGeneratorAgent(provider).run({
        "scenarios": scenarios,
        "selector_hints": inspector_result.selector_hints,
    })

    Path("results").mkdir(exist_ok=True)
    Path("results/feature_snapshot.txt").write_text(feature_text, encoding="utf-8")

    files_to_push = {
        "results/test_cases.md": test_cases_md,
        "results/playwright.spec.ts": playwright_spec,
        "results/scenarios.json": json.dumps(scenarios, indent=2),
        "results/feature_snapshot.txt": feature_text,
    }

    log("Pushing results to GitHub...")
    from integrations.github_sync import GithubSync
    commit_sha = GithubSync().push_results(files_to_push, "chore: update QA artifacts")
    log(f"Pushed commit: {commit_sha}")

    log("Waiting for GitHub Actions...")
    import requests
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPO"]
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    run_id: int | None = None
    deadline = time.time() + 300
    while time.time() < deadline:
        time.sleep(10)
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/actions/runs",
            headers=headers,
            params={"branch": os.getenv("GITHUB_BRANCH", "main"), "per_page": 5},
        )
        for run in resp.json().get("workflow_runs", []):
            if run.get("head_sha") == commit_sha:
                status = run["status"]
                log(f"Run status: {status}")
                if status == "completed":
                    run_id = run["id"]
                    break
        if run_id:
            break

    artifacts_dir = Path("results/artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    if run_id:
        art_resp = requests.get(
            f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts",
            headers=headers,
        )
        for artifact in art_resp.json().get("artifacts", []):
            dl = requests.get(
                f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact['id']}/zip",
                headers=headers,
            )
            path = artifacts_dir / f"{artifact['name']}.zip"
            path.write_bytes(dl.content)
            log(f"Downloaded artifact: {path}")

    from integrations.google_drive import GoogleDriveClient
    drive = GoogleDriveClient(sa_path)
    output_folder_id = os.environ["GOOGLE_DRIVE_OUTPUT_FOLDER_ID"]
    dated_folder_id = drive.get_or_create_subfolder(
        output_folder_id, datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    drive_link = f"https://drive.google.com/drive/folders/{dated_folder_id}"

    for f in artifacts_dir.iterdir():
        drive.upload_file(str(f), dated_folder_id)
        log(f"Uploaded {f.name} to Drive")

    from integrations.gmail import GmailClient
    gmail = GmailClient(sa_path, os.environ["GMAIL_SENDER"])
    gmail.send(
        to=os.environ["GMAIL_RECIPIENT"],
        subject="QA Pipeline Complete",
        body=f"Run complete. Artifacts: {drive_link}\nCommit: {commit_sha}",
    )
    log("Gmail summary sent.")


if __name__ == "__main__":
    main()