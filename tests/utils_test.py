import copy
import json

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


def test_trim_state():
    for i in range(4):
        with open(f"tests/fixtures/large_state_{i}.json", "r") as f:
            original_state = json.load(f)
        state = copy.deepcopy(original_state)
        trimmed_state = trim_state(state, state["context_trimming_threshold"])
        assert trimmed_state != original_state, f"state {i} is not trimmed"
        assert len(json.dumps(original_state)) > len(
            json.dumps(trimmed_state)
        ), f"state {i} is not trimmed"
        assert (
            len(json.dumps(trimmed_state)) < 1_000_000
        ), f"trimmed state {i} is still too large"
