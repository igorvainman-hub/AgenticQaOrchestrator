.PHONY: install lint test dry-run poll docker-build

install:
	uv sync --all-extras
	uv run playwright install chromium --with-deps
	npm install

lint:
	uv run ruff check .
	uv run mypy agents/ integrations/ orchestrator.py poll_and_run.py

test:
	uv run pytest tests/ -v

dry-run:
	uv run python orchestrator.py --file my_feature.txt --dry-run-llm

poll:
	uv run python poll_and_run.py

docker-build:
	docker build -t qa-orchestrator .