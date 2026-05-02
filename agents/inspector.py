from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from agents.base import BaseAgent

SKIP_PATH_SEGMENTS = {"/api/", "/v1/", "/auth/"}
MAX_DOM_CHARS = 40_000


@dataclass
class DomSnapshot:
    url: str
    stage: str           # "initial" | "after_interaction"
    dom: str


@dataclass
class InspectorResult:
    snapshots: list[DomSnapshot] = field(default_factory=list)
    selector_hints: dict[str, Any] = field(default_factory=dict)


def _should_skip_url(url: str) -> bool:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path
    if any(seg in path for seg in SKIP_PATH_SEGMENTS):
        return True
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 3 and not path.endswith(".html"):
        return True
    return False


def _clean_dom(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "svg", "noscript", "meta", "link"]):
        tag.decompose()
    return str(soup)[:MAX_DOM_CHARS]


class _SelectorMapperAgent(BaseAgent):
    def __init__(self, provider: str) -> None:
        super().__init__("prompts/inspector_prompt.txt", provider)

    def run(self, snapshots: list[DomSnapshot]) -> dict[str, Any]:
        payload = json.dumps([
            {"url": s.url, "stage": s.stage, "dom": s.dom} for s in snapshots
        ])

        def parse(raw: str) -> dict[str, Any]:
            raw = raw.strip()
            return json.loads(raw)

        return self._invoke_with_retry(payload, parse, "SelectorMapper")


class InspectorAgent(BaseAgent):
    def __init__(self, provider: str = "openai") -> None:
        # BaseAgent init not used directly; mapper handles LLM calls
        self.provider = provider

    def run(self, feature_text: str) -> InspectorResult:
        urls = re.findall(r"https?://\S+", feature_text)
        urls = [u.rstrip(".,;)") for u in urls if not _should_skip_url(u)]

        quoted_strings = re.findall(r'"([^"]{2,80})"', feature_text)
        snapshots: list[DomSnapshot] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()

            for url in urls:
                try:
                    page.goto(url, wait_until="load")
                    for selector in ["main", "form", "button"]:
                        try:
                            page.wait_for_selector(selector, timeout=3000)
                            break
                        except Exception:
                            continue

                    initial_dom = _clean_dom(page.content())
                    snapshots.append(DomSnapshot(url=url, stage="initial", dom=initial_dom))

                    # Attempt one interaction
                    for text in quoted_strings:
                        try:
                            locator = page.get_by_role("button", name=re.compile(text, re.I))
                            if locator.count() > 0:
                                locator.first.click()
                                post_dom = _clean_dom(page.content())
                                snapshots.append(DomSnapshot(url=url, stage="after_interaction", dom=post_dom))
                                break
                        except Exception:
                            continue
                except Exception:
                    continue

            browser.close()

        mapper = _SelectorMapperAgent(self.provider)
        selector_hints = mapper.run(snapshots) if snapshots else {}
        return InspectorResult(snapshots=snapshots, selector_hints=selector_hints)