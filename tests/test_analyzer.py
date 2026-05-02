from __future__ import annotations

import json
import pytest
from agents.analyzer import AnalyzerAgent


def test_analyzer_returns_scenarios(mocker):
    mock = mocker.patch("agents.base.BaseAgent._invoke_with_retry")
    mock.return_value = {"scenarios": [{"id": "S1", "category": "happy_path", "title": "t", "description": "d", "test_data": ["k: v"]}]}
    agent = AnalyzerAgent.__new__(AnalyzerAgent)
    agent.llm = None
    agent.system_prompt = ""
    agent._invoke_with_retry = mock
    result = agent.run("some feature text")
    assert "scenarios" in result


def test_analyzer_raises_on_invalid_json(mocker):
    mock = mocker.patch("agents.base.BaseAgent._invoke_with_retry", side_effect=RuntimeError("failed"))
    agent = AnalyzerAgent.__new__(AnalyzerAgent)
    agent._invoke_with_retry = mock
    with pytest.raises(RuntimeError):
        agent.run("bad input")