# AgenticQaOrchestrator

## What it does
AgenticQaOrchestrator is a multi-agent QA pipeline that takes a feature description from a local text file or Google Docs, runs four sequential AI agents to inspect UI selectors, derive structured scenarios, generate markdown test cases, and produce a runnable Playwright spec, then pushes artifacts to GitHub, waits for CI execution, uploads results to Google Drive, and sends a Gmail summary.

## Architecture
```text
Google Drive (input folder)
    ?  new_feature.txt dropped manually
    ?
drive_poll.yml (cron 09:00 UTC)
    ?
    ?
poll_and_run.py ??? move to /processed/
    ?
    ?
orchestrator.py
    ?
    ??? Agent 0: InspectorAgent  ??? selector_hints
    ??? Agent 1: AnalyzerAgent   ??? scenarios.json
    ??? Agent 2: TestWriterAgent ??? test_cases.md
    ??? Agent 3: PlaywrightGen   ??? playwright.spec.ts + feature_snapshot.txt
                                              ?
                                              ?
                                    GitHub (single commit)
                                              ?
                                              ?
                               qa_pipeline.yml (Playwright run)
                               BASE_URL ? feature_snapshot.txt
                                              ?
                                              ?
                               Google Drive (artifacts) + Gmail
```

## Quick start
```bash
uv sync --all-extras
npm install
cp .env.example .env
make dry-run
```

## Full run
Prerequisites:
- Google Cloud project with Drive, Docs, and Gmail APIs enabled.
- Service account JSON available locally (for example in `./credentials/service_account.json`).
- Access to required Google Drive folders (input, processed, output) and Gmail delegated sender.
- GitHub personal access token with access to the target repository.
- Environment variables configured in `.env`.

Run the full pipeline:
```bash
uv run python orchestrator.py --file my_feature.txt
```

Or from Google Docs:
```bash
uv run python orchestrator.py --doc-id GOOGLE_DOC_ID
```

## Drive polling
To use polling mode, drop `new_feature.txt` into the configured Google Drive input folder (`GOOGLE_DRIVE_INPUT_FOLDER_ID`).
When `drive_poll.yml` runs, it executes `poll_and_run.py`, which downloads today's `new_feature.txt`, writes it locally, moves it to the processed folder, and launches `orchestrator.py`.
You can also trigger it manually from GitHub Actions using **workflow_dispatch** on the `Drive Poll` workflow.

## Docker usage
```bash
docker build -t qa-orchestrator .
docker run --rm \
  --env-file .env \
  -v $(pwd)/credentials:/app/credentials:ro \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/my_feature.txt:/app/feature.txt:ro \
  qa-orchestrator --file /app/feature.txt
```

## Environment variables
| name | required | description |
|---|---|---|
| OPENAI_API_KEY | yes (if `LLM_PROVIDER=openai`) | OpenAI API key for LLM calls. |
| ANTHROPIC_API_KEY | yes (if `LLM_PROVIDER=anthropic`) | Anthropic API key for LLM calls. |
| LLM_PROVIDER | yes | LLM backend: `openai` or `anthropic`. |
| GOOGLE_SERVICE_ACCOUNT_JSON | yes | Path to Google service account JSON file. |
| GOOGLE_DRIVE_INPUT_FOLDER_ID | yes (poll mode) | Drive folder ID watched for `new_feature.txt`. |
| GOOGLE_DRIVE_PROCESSED_FOLDER_ID | yes (poll mode) | Drive folder ID where processed input files are moved. |
| GOOGLE_DRIVE_OUTPUT_FOLDER_ID | yes | Drive folder ID where pipeline artifacts are uploaded. |
| GMAIL_SENDER | yes | Gmail sender identity used with domain-wide delegation. |
| GMAIL_RECIPIENT | yes | Recipient email for pipeline summary. |
| GITHUB_TOKEN | yes | Token used to push generated artifacts and query Actions API. |
| GITHUB_REPO | yes | Target repo in `owner/repo` format. |
| GITHUB_BRANCH | yes | Target branch for commits (default `main`). |

## Makefile commands
| command | description |
|---|---|
| `make install` | Install Python/Node dependencies and Playwright browser. |
| `make lint` | Run Ruff and mypy checks. |
| `make test` | Run pytest test suite. |
| `make dry-run` | Execute local LLM-only pipeline using `my_feature.txt`. |
| `make poll` | Run Drive polling entrypoint locally. |
| `make docker-build` | Build Docker image `qa-orchestrator`. |

## Google Cloud setup
1. Create or select a Google Cloud project.
2. Enable APIs: Google Drive API, Google Docs API, and Gmail API.
3. Create a service account and generate a JSON key.
4. If using Gmail send, configure domain-wide delegation for the service account and authorize Gmail send scope.
5. Share input/processed/output Google Drive folders with the service account email.
6. Save the JSON key file locally and point `GOOGLE_SERVICE_ACCOUNT_JSON` to it.

## GitHub setup
1. Create a PAT for orchestrator pushes with scopes needed for repository contents and Actions read access.
2. Add repository secrets:
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
   - `GOOGLE_DRIVE_INPUT_FOLDER_ID`
   - `GOOGLE_DRIVE_PROCESSED_FOLDER_ID`
   - `GOOGLE_DRIVE_OUTPUT_FOLDER_ID`
   - `GMAIL_SENDER`
   - `GMAIL_RECIPIENT`
   - `ORCHESTRATOR_GITHUB_TOKEN`
   - `ADMIN_USERNAME`
   - `ADMIN_PASSWORD`
3. Add repository variable:
   - `LLM_PROVIDER`
4. Ensure default branch is `main` and workflow permissions allow required Actions operations.