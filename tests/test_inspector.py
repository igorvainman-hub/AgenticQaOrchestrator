from __future__ import annotations

import pytest
from agents.inspector import InspectorAgent, InspectorResult, _should_skip_url


def test_skip_api_url():
    assert _should_skip_url("https://example.com/api/users") is True


def test_skip_v1_url():
    assert _should_skip_url("https://example.com/v1/endpoint") is True


def test_skip_deep_path():
    assert _should_skip_url("https://example.com/a/b/c/d") is True


def test_allow_normal_url():
    assert _should_skip_url("https://example.com/login") is False


def test_inspector_returns_result(mocker):
    mocker.patch("agents.inspector.sync_playwright")
    mocker.patch("agents.inspector._SelectorMapperAgent.run", return_value={"selectors": []})

    agent = InspectorAgent.__new__(InspectorAgent)
    agent.provider = "openai"

    result = agent.run("Base URL: https://v1/skip-this.com\nSome feature text.")
    assert isinstance(result, InspectorResult)