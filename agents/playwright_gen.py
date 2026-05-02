from __future__ import annotations

import json

from agents.base import BaseAgent


class PlaywrightGeneratorAgent(BaseAgent):
    def __init__(self, provider: str = "openai") -> None:
        super().__init__("prompts/playwright_prompt.txt", provider)

    def run(self, payload: dict) -> str:
        """payload must have keys: 'scenarios' and 'selector_hints'"""
        user_content = json.dumps(payload)

        def parse(raw: str) -> str:
            cleaned = self._strip_code_fences(raw)
            if not cleaned:
                raise ValueError("Empty response from PlaywrightGeneratorAgent")
            return cleaned

        return self._invoke_with_retry(user_content, parse, "PlaywrightGeneratorAgent")