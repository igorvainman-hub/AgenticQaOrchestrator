FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

COPY agents/ agents/
COPY integrations/ integrations/
COPY prompts/ prompts/
COPY scripts/ scripts/
COPY playwright.config.ts .
COPY orchestrator.py .

RUN uv run playwright install chromium --with-deps

ENTRYPOINT ["uv", "run", "python", "orchestrator.py"]