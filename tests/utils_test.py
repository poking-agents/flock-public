import copy
import json
import pathlib

import pytest

from utils.functions import parse_completions_function_call
from utils.state import trim_state


@pytest.mark.parametrize(
    "function_names, completion, func_name_to_args, expected",
    [
        (
            ["advise"],
            "```advise\nyour advise to the agent\n```python\ncode 1\n```\n```",
            {"advise": ("advice", str)},
            {
                "name": "advise",
                "arguments": '{"advice": "your advise to the agent\\n```python\\ncode 1\\n```"}',
            },
        ),
        (
            ["python", "bash"],
            "some thoughts\n```python\ncode 1\n```\n```bash\ncode 2\n```",
            {"python": ("code", str), "bash": ("code", str)},
            {
                "name": "python",
                "arguments": '{"code": "code 1"}',
            },
        ),
        (
            ["python", "bash"],
            "some thoughts",
            {"python": ("code", str), "bash": ("code", str)},
            None,
        ),
        (
            ["python", "bash"],
            "```python\n```",
            {"python": ("code", str), "bash": ("code", str)},
            None,
        ),
        (
            ["set_timeout"],
            "some thoughts\n```set_timeout\nblah\n```",
            {"set_timeout": ("timeout", int)},
            None,
        ),
    ],
)
def test_parse_completions_function_call(
    function_names, completion, func_name_to_args, expected
):
    function_call = parse_completions_function_call(
        False, function_names, completion, func_name_to_args
    )
    assert (
        function_call == expected
    ), f"actual function call: {function_call}, expected function call: {expected}"


@pytest.mark.parametrize(
    "large_state_file_name",
    [f"large_state_{i}.json" for i in range(4)],
)
def test_trim_state(large_state_file_name: str):
    with open(
        pathlib.Path(__file__).resolve().parent / "fixtures" / large_state_file_name,
        "r",
    ) as f:
        original_state = json.load(f)
    state = copy.deepcopy(original_state)
    trimmed_state = trim_state(state, state["context_trimming_threshold"])
    assert (
        trimmed_state != original_state
    ), f"state {large_state_file_name} is not trimmed"
    assert len(json.dumps(original_state)) > len(
        json.dumps(trimmed_state)
    ), f"state {large_state_file_name} is not trimmed"
    assert (
        len(json.dumps(trimmed_state)) < 1_000_000
    ), f"trimmed state {large_state_file_name} is still too large"
