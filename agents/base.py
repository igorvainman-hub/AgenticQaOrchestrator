from __future__ import annotations

import time
import logging
from typing import Any, Callable, TypeVar

T = TypeVar("T")
MAX_ATTEMPTS = 3

log = logging.getLogger(__name__)


class BaseAgent:
    def __init__(self, prompt_path: str, provider: str = "openai") -> None:
        with open(prompt_path, encoding="utf-8") as f:
            self.system_prompt = f.read()
        self.llm = self._build_llm(provider)

    def _build_llm(self, provider: str) -> Any:
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model="claude-3-5-sonnet-latest", temperature=0)
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o", temperature=0)

    def _invoke_with_retry(
        self,
        user_content: str,
        parse_response: Callable[[str], T],
        step_name: str,
        should_retry: Callable[[Exception], bool] | None = None,
    ) -> T:
        from langchain_core.messages import HumanMessage, SystemMessage

        last_exc: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                messages = [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=user_content),
                ]
                response = self.llm.invoke(messages)
                return parse_response(response.content)
            except Exception as exc:
                last_exc = exc
                if should_retry is not None and not should_retry(exc):
                    raise
                log.warning("%s attempt %d/%d failed: %s", step_name, attempt + 1, MAX_ATTEMPTS, exc)
                if attempt < MAX_ATTEMPTS - 1:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"{step_name} failed after {MAX_ATTEMPTS} attempts") from last_exc