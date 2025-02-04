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
    ],
)
def test_parse_backticks_function_call(
    function_names, completion, func_name_to_args, expected
):
    actual = parse_completions_function_call(
        False, function_names, completion, func_name_to_args
    )
    assert actual == expected, f"actual: {actual}, expected: {expected}"
