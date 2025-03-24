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
                "arguments": (
                    '{"advice": "your advise to the agent\\n```python\\ncode 1\\n```"}'
                ),
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
    "original_state",
    [
        # Case 1: Long tool output content
        {
            "nodes": [
                {
                    "source": "tool_output",
                    "options": [
                        {
                            "name": "run_bash",
                            "content": "really long tool output " * 100_000,
                            "metadata": {},
                            "function_call": None,
                        },
                    ],
                },
            ],
            "previous_results": [],
            "context_trimming_threshold": 80_000,
        },
        # Case 2: Long stdout in bash result
        {
            "nodes": [],
            "previous_results": [
                [
                    {
                        "type": "bash",
                        "error": None,
                        "result": {
                            "status": 0,
                            "stderr": "",
                            "stdout": "really long stdout output " * 100_000,
                        },
                    },
                ]
            ],
            "context_trimming_threshold": 80_000,
        },
        # Case 3: Long stderr in bash result
        {
            "nodes": [],
            "previous_results": [
                [
                    {
                        "type": "bash",
                        "error": None,
                        "result": {
                            "status": 0,
                            "stderr": "really long stderr output " * 100_000,
                            "stdout": "",
                        },
                    },
                ]
            ],
            "context_trimming_threshold": 80_000,
        },
        # Case 4: Long python output
        {
            "nodes": [],
            "previous_results": [
                [
                    {
                        "type": "python",
                        "error": None,
                        "result": {
                            "error": None,
                            "output": "really long python result " * 100_000,
                        },
                    },
                ]
            ],
            "context_trimming_threshold": 80_000,
        },
        # Case 5: Multiple long outputs combined
        {
            "nodes": [
                {
                    "source": "tool_output",
                    "options": [
                        {
                            "name": "run_bash",
                            "content": "really long tool output " * 100_000,
                            "metadata": {},
                            "function_call": None,
                        },
                    ],
                },
            ],
            "previous_results": [
                [
                    {
                        "type": "bash",
                        "error": None,
                        "result": {
                            "status": 0,
                            "stderr": "really long stderr " * 100_000,
                            "stdout": "really long stdout " * 100_000,
                        },
                        "metadata": {},
                    },
                    {
                        "type": "python",
                        "error": None,
                        "result": {
                            "error": None,
                            "output": "really long python result " * 100_000,
                        },
                        "metadata": {},
                    },
                ]
            ],
            "context_trimming_threshold": 80_000,
        },
    ],
)
def test_trim_state(original_state: dict[str, any]):
    state = copy.deepcopy(original_state)
    trimmed_state = trim_state(state, state["context_trimming_threshold"])
    assert len(json.dumps(original_state)) > len(
        json.dumps(trimmed_state)
    ), "state is not trimmed"
    assert (
        len(json.dumps(trimmed_state)) < 1_000_000
    ), "trimmed state is still too large"
