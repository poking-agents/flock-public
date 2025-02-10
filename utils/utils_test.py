import pytest

from utils.functions import parse_completions_function_call, get_completions_without_cot


@pytest.mark.parametrize(
    "function_names, completion, func_name_to_args, expected",
    [
        (
            ["advise"],
            "```advise\nyour advise to the agent\n```python\ncode 1\n```\n```",
            {"advise": ("advice", str)},
            (
                {
                    "name": "advise",
                    "arguments": '{"advice": "your advise to the agent\\n```python\\ncode 1\\n```"}',
                },
                "",
            ),
        ),
        (
            ["python", "bash"],
            "some thoughts\n```python\ncode 1\n```\n```bash\ncode 2\n```",
            {"python": ("code", str), "bash": ("code", str)},
            (
                {
                    "name": "python",
                    "arguments": '{"code": "code 1"}',
                },
                "some thoughts\n",
            ),
        ),
        (
            ["python", "bash"],
            "some thoughts",
            {"python": ("code", str), "bash": ("code", str)},
            (
                None,
                "some thoughts",
            ),
        ),
        (
            ["python", "bash"],
            "```python\n```",
            {"python": ("code", str), "bash": ("code", str)},
            (
                None,
                "",
            ),
        ),
        (
            ["set_timeout"],
            "some thoughts\n```set_timeout\nblah\n```",
            {"set_timeout": ("timeout", int)},
            (
                None,
                "some thoughts\n",
            ),
        ),
    ],
)
def test_parse_completions_function_call(
    function_names, completion, func_name_to_args, expected
):
    function_call, completion = parse_completions_function_call(
        False, function_names, completion, func_name_to_args
    )
    actual_function_call, actual_completion = expected
    assert (
        function_call == actual_function_call
    ), f"actual function call: {function_call}, expected function call: {actual_function_call}"
    assert (
        completion == actual_completion
    ), f"actual completion: {completion}, expected completion: {actual_completion}"


@pytest.mark.parametrize(
    "completion, expected",
    [
        (
            "<think>\nsome thoughts\n</think>some function call",
            "some function call",
        ),
        (
            "<think>\nsome thoughts\nsome function call",
            "\nsome thoughts\nsome function call",
        ),
    ],
)
def test_get_completions_without_cot(completion, expected):
    assert (
        get_completions_without_cot(completion) == expected
    ), f"actual completion: {get_completions_without_cot(completion)}, \nexpected completion: {expected}"
