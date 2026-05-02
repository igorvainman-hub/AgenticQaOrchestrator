from __future__ import annotations

import json

from agents.base import BaseAgent


class TestWriterAgent(BaseAgent):
    def __init__(self, provider: str = "openai") -> None:
        super().__init__("prompts/test_writer_prompt.txt", provider)

    def run(self, scenarios: dict) -> str:
        user_content = json.dumps(scenarios)

        def parse(raw: str) -> str:
            if not raw.strip():
                raise ValueError("Empty response from TestWriterAgent")
            if "#" not in raw:
                raise ValueError("Response missing heading marker '#'")
            if len(raw.split()) < 5:
                raise ValueError("Response too short")
            return raw

        return self._invoke_with_retry(user_content, parse, "TestWriterAgent")