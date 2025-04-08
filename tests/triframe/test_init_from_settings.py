import json
from unittest.mock import mock_open, patch

import pytest

from flock.triframe.phases.init_from_settings import initialize_state_from_settings


@pytest.mark.parametrize(
    "test_state",
    [
        {
            "actors": [
                {
                    "max_reasoning_tokens": 10000,
                    "max_tokens": 20000,
                    "model": "claude-3-7-sonnet-20250219",
                    "n": 3,
                    "temp": 1.0,
                }
            ],
            "advisors": [
                {
                    "max_reasoning_tokens": 10000,
                    "max_tokens": 20000,
                    "model": "claude-3-7-sonnet-20250219",
                    "n": 1,
                    "temp": 1.0,
                }
            ],
            "enable_advising": True,
            "intermediate_scoring": False,
            "limit_type": "token",
            "raters": [
                {
                    "max_reasoning_tokens": 10000,
                    "max_tokens": 20000,
                    "model": "claude-3-7-sonnet-20250219",
                    "n": 2,
                    "temp": 1.0,
                }
            ],
            "require_function_call": False,
        },
    ],
)
def test_initialize_state_from_settings(test_state: dict):
    mock_file_content = json.dumps(test_state)
    with patch("builtins.open", mock_open(read_data=mock_file_content)):
        state = initialize_state_from_settings("test", "dummy_path.json")

        assert state.settings.advisors[0].model == test_state["advisors"][0]["model"]
        assert (
            state.settings.advisors[0].max_tokens
            == test_state["advisors"][0]["max_tokens"]
        )
        assert (
            state.settings.advisors[0].max_reasoning_tokens
            == test_state["advisors"][0]["max_reasoning_tokens"]
        )
        assert state.settings.actors[0].model == test_state["actors"][0]["model"]
        assert (
            state.settings.actors[0].max_tokens == test_state["actors"][0]["max_tokens"]
        )
        assert (
            state.settings.actors[0].max_reasoning_tokens
            == test_state["actors"][0]["max_reasoning_tokens"]
        )
        assert state.settings.raters[0].model == test_state["raters"][0]["model"]
        assert (
            state.settings.raters[0].max_tokens == test_state["raters"][0]["max_tokens"]
        )
        assert (
            state.settings.raters[0].max_reasoning_tokens
            == test_state["raters"][0]["max_reasoning_tokens"]
        )
