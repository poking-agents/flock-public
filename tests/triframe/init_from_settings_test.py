import json
import pathlib

from triframe.phases.init_from_settings import initialize_state_from_settings


def test_initialize_state_from_settings():
    with open(
        pathlib.Path(__file__).parent.parent / "fixtures" / "triframe_state.json",
        "r",
    ) as f:
        expected_state = json.load(f)
    state = initialize_state_from_settings("test", "tests/fixtures/triframe_state.json")
    assert state.settings.advisors[0].model == expected_state["advisors"][0]["model"]
    assert (
        state.settings.advisors[0].max_tokens
        == expected_state["advisors"][0]["max_tokens"]
    )
    assert (
        state.settings.advisors[0].max_reasoning_tokens
        == expected_state["advisors"][0]["max_reasoning_tokens"]
    )
    assert state.settings.actors[0].model == expected_state["actors"][0]["model"]
    assert (
        state.settings.actors[0].max_tokens == expected_state["actors"][0]["max_tokens"]
    )
    assert (
        state.settings.actors[0].max_reasoning_tokens
        == expected_state["actors"][0]["max_reasoning_tokens"]
    )
    assert state.settings.raters[0].model == expected_state["raters"][0]["model"]
    assert (
        state.settings.raters[0].max_tokens == expected_state["raters"][0]["max_tokens"]
    )
    assert (
        state.settings.raters[0].max_reasoning_tokens
        == expected_state["raters"][0]["max_reasoning_tokens"]
    )
