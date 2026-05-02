from __future__ import annotations

from agents.base import BaseAgent


class AnalyzerAgent(BaseAgent):
    def __init__(self, provider: str = "openai") -> None:
        super().__init__("prompts/analyzer_prompt.txt", provider)

    def run(self, feature_text: str) -> dict:
        def parse(raw: str) -> dict:
            return self._parse_json_object_response(
                raw,
                step_name="AnalyzerAgent",
                required_keys=("scenarios",),
            )

        return self._invoke_with_retry(feature_text, parse, "AnalyzerAgent")