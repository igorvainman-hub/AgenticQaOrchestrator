from __future__ import annotations

import json
import re
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
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
            raw_response: str | None = None
            try:
                messages = [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=user_content),
                ]
                response = self.llm.invoke(messages)
                raw_response = str(response.content)
                return parse_response(raw_response)
            except Exception as exc:
                last_exc = exc
                if raw_response is not None and isinstance(exc, (json.JSONDecodeError, ValueError)):
                    self._dump_failed_response(step_name, attempt + 1, raw_response, exc)
                if should_retry is not None and not should_retry(exc):
                    raise
                log.warning("%s attempt %d/%d failed: %s", step_name, attempt + 1, MAX_ATTEMPTS, exc)
                if attempt < MAX_ATTEMPTS - 1:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"{step_name} failed after {MAX_ATTEMPTS} attempts") from last_exc

    @staticmethod
    def _strip_code_fences(raw: str) -> str:
        return re.sub(r"```(?:[a-zA-Z0-9_+-]+)?|```", "", raw).strip()

    @classmethod
    def _parse_json_object_response(
        cls,
        raw: str,
        step_name: str,
        required_keys: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        cleaned = cls._strip_code_fences(raw)
        if not cleaned:
            raise ValueError(f"Empty response from {step_name}")

        candidates: list[str] = []

        # Prefer the full cleaned response when it already looks like JSON.
        if cleaned.startswith("{") and cleaned.endswith("}"):
            candidates.append(cleaned)

        # Fallback 1: naive first/last brace slice.
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            sliced = cleaned[start : end + 1]
            if sliced not in candidates:
                candidates.append(sliced)

        # Fallback 2: first balanced JSON object to ignore trailing chatter.
        balanced = cls._extract_first_balanced_json_object(cleaned)
        if balanced and balanced not in candidates:
            candidates.append(balanced)

        if not candidates:
            raise ValueError(f"{step_name} did not return JSON object")

        parse_error: json.JSONDecodeError | None = None
        result: dict[str, Any] | None = None
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:
                parse_error = exc
                continue
            if not isinstance(parsed, dict):
                raise ValueError(f"{step_name} did not return a JSON object at top level")
            result = parsed
            break

        if result is None:
            snippet = cleaned[:300].replace("\n", "\\n")
            if parse_error is not None:
                raise ValueError(
                    f"{step_name} returned invalid JSON: {parse_error}. Response snippet: {snippet}"
                ) from parse_error
            raise ValueError(f"{step_name} returned invalid JSON. Response snippet: {snippet}")

        missing = [k for k in required_keys if k not in result]
        if missing:
            raise ValueError(f"{step_name} response missing keys: {missing}")
        return result

    @staticmethod
    def _extract_first_balanced_json_object(text: str) -> str | None:
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escaped = False

        for idx in range(start, len(text)):
            ch = text[idx]
            if in_string:
                if escaped:
                    escaped = False
                    continue
                if ch == "\\":
                    escaped = True
                    continue
                if ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]

        return None

    @staticmethod
    def _dump_failed_response(step_name: str, attempt_no: int, raw_response: str, exc: Exception) -> None:
        try:
            out_dir = Path("results/debug")
            out_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            file_path = out_dir / f"{step_name.lower()}_attempt{attempt_no}_{stamp}.txt"
            body = (
                f"step={step_name}\n"
                f"attempt={attempt_no}\n"
                f"error={type(exc).__name__}: {exc}\n"
                "----- RAW RESPONSE START -----\n"
                f"{raw_response}\n"
                "----- RAW RESPONSE END -----\n"
            )
            file_path.write_text(body, encoding="utf-8")
            log.warning("%s parse failed; raw response saved to %s", step_name, file_path.as_posix())
        except Exception as dump_exc:
            log.warning("Failed to persist raw response for %s: %s", step_name, dump_exc)