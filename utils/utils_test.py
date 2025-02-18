import pytest

from utils.functions import parse_completions_function_call


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
