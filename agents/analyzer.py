from __future__ import annotations

import json
import re

from agents.base import BaseAgent


class AnalyzerAgent(BaseAgent):
    def __init__(self, provider: str = "openai") -> None:
        super().__init__("prompts/analyzer_prompt.txt", provider)

    def run(self, feature_text: str) -> dict:
        def parse(raw: str) -> dict:
            cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
            result = json.loads(cleaned)
            if "scenarios" not in result:
                raise ValueError("Missing 'scenarios' key in LLM response")
            return result

        def should_retry(exc: Exception) -> bool:
            return not isinstance(exc, (json.JSONDecodeError, ValueError))

        return self._invoke_with_retry(feature_text, parse, "AnalyzerAgent", should_retry)