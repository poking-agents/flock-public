import pytest

from utils.functions import parse_backticks_function_call


@pytest.mark.parametrize(
    "function_name, completion, func_name_to_args, expected",
    [
        (
            "advise",
            "```advise\nyour advise to the agent\n```",
            {"advise": ("advice", str)},
            {"name": "advise", "arguments": {"advice": "your advise to the agent"}},
        ),
        (
            "python",
            "```python\nprint('hello')\n```",
            {"python": ("code", str)},
            {"name": "python", "arguments": {"code": "print('hello')"}},
        ),
        (
            "set_timeout",
            "```set_timeout\n10\n```",
            {"set_timeout": ("timeout", int)},
            {"name": "set_timeout", "arguments": {"timeout": 10}},
        ),
        (
            "bash",
            "```bash\nls\n```",
            {"bash": ("command", str)},
            {"name": "bash", "arguments": {"command": "ls"}},
        ),
        (
            "submit",
            "```submit\n123\n```",
            {"submit": ("submission_id", str)},
            {"name": "submit", "arguments": {"submission_id": "123"}},
        ),
        ("score", "```score\n```", {"score": ()}, {"name": "score", "arguments": {}}),
        (
            "score_log",
            "```score_log\n```",
            {"score_log": ()},
            {"name": "score_log", "arguments": {}},
        ),
        (
            "set_timeout",
            "```set_timeout\ntimeout=10\n```",
            {"set_timeout": ("timeout", int)},
            None,
        ),
        ("set_timeout", "```set_timeout\n```", {"set_timeout": ("timeout", int)}, None),
        ("advise", "```advise\n```", {"advise": ("advice", str)}, None),
        ("python", "```python```", {"python": ("code", str)}, None),
    ],
)
def test_parse_backticks_function_call(
    function_name, completion, func_name_to_args, expected
):
    assert (
        parse_backticks_function_call(function_name, completion, func_name_to_args)
        == expected
    )
