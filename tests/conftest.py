from __future__ import annotations

import pytest


@pytest.fixture
def sample_feature_text() -> str:
    return (
        "Base URL: https://example.com\n"
        "Feature: Admin can create a new user by clicking \"Add New User\"."
    )


@pytest.fixture
def sample_scenarios_json() -> dict:
    return {
        "scenarios": [
            {
                "id": "S1",
                "category": "happy_path",
                "title": "test",
                "description": "desc",
                "test_data": ["key: value"],
            }
        ]
    }


@pytest.fixture
def mock_llm_response(mocker):
    return mocker.patch("agents.base.BaseAgent._invoke_with_retry")