"""Logging utilities for triframe workflow"""

import json
from typing import Any, Dict

from triframe.styles import log_styles
from type_defs import Option
from type_defs.operations import LogWithAttributesParams, LogWithAttributesRequest


def create_log_request(content: str, style: dict) -> LogWithAttributesRequest:
    """Create a log request with the given content and style"""
    return LogWithAttributesRequest(
        type="log_with_attributes",
        params=LogWithAttributesParams(content=content, attributes=style),
    )


def log_actor_choice(option: Option) -> LogWithAttributesRequest:
    """Log an actor's choice with appropriate styling"""
    message = ""
    style = log_styles["actor_no_function"]  # Default style for no function call

    if option.content:
        message += f"Completion content:\n{option.content}\n"

    if option.function_call is not None:
        try:
            function_name = option.function_call["name"]
            # Select style based on function name
            if function_name == "run_bash":
                style = log_styles["actor_bash"]
            elif function_name == "run_python":
                style = log_styles["actor_python"]
            elif function_name == "submit":
                style = log_styles["actor_submit"]
            elif function_name in ["score", "score_log"]:
                style = log_styles["actor_score"]
            else:
                style = log_styles["actor"]  # Default actor style for unknown functions

            message += f"Function called: {function_name}"
            if function_name not in ["score", "score_log"]:
                first_key_in_args = next(
                    iter(json.loads(option.function_call["arguments"]))
                )
                message += f" with {first_key_in_args}:\n"
                message += f"{json.loads(option.function_call['arguments'])[first_key_in_args]}\n"
        except json.JSONDecodeError:
            message += f"Function call does not parse: {option.function_call}\n"
            style = log_styles["warning"]
        except KeyError:
            message += (
                f"Function call does not contain arguments: {option.function_call}\n"
            )
            style = log_styles["warning"]

    return create_log_request(message, style)


def log_advisor_choice(option: Option) -> LogWithAttributesRequest:
    """Log an advisor's choice with appropriate styling"""
    message = ""
    style = log_styles["advisor"]
    if option.content:
        message += f"Completion content:\n{option.content}\n"
    if option.function_call is not None:
        try:
            advice = json.loads(option.function_call["arguments"])["advice"]
            message += f"Advice:\n{advice}"
        except json.JSONDecodeError:
            message += f"Function call does not parse and contain 'advice': {option.function_call}\n"
            style = log_styles["warning"]
        except KeyError:
            message += (
                f"Function call does not contain 'advice': {option.function_call}\n"
            )
            style = log_styles["warning"]
    return create_log_request(message, style)


def log_tool_output(content: str) -> LogWithAttributesRequest:
    """Log tool output with appropriate styling"""
    return create_log_request(content, log_styles["tool_output"])


def log_review(content: str) -> LogWithAttributesRequest:
    """Log a review with appropriate styling"""
    return create_log_request(content, log_styles["review"])


def log_warning(content: str) -> LogWithAttributesRequest:
    """Log a warning with appropriate styling"""
    return create_log_request(content, log_styles["warning"])


def format_ratings(function_call: Dict[str, Any]) -> str:
    """Format ratings from a function call into a readable string"""
    try:
        if not function_call or function_call.get("name") != "rate_options":
            return ""

        ratings = json.loads(function_call["arguments"])["ratings"]
        formatted_parts = []

        for rating in ratings:
            formatted_parts.append(
                f"Option {rating['option_index']}: {rating['rating']:+.1f}\n"
                f"  {rating['comment']}"
            )

        return "\n".join(formatted_parts)
    except (json.JSONDecodeError, KeyError, TypeError):
        return "Error parsing ratings"


def log_advisor_choosing(option: Option) -> LogWithAttributesRequest:
    """Log advisor's choice process with appropriate styling"""
    message = ""
    if option.content:
        message += f"Completion content:\n{option.content}\n"
    if option.function_call:
        message += format_ratings(option.function_call)
    return create_log_request(message, log_styles["advisor_choosing"])


def log_system(content: str) -> LogWithAttributesRequest:
    """Log system messages with appropriate styling"""
    return create_log_request(content, log_styles["system"])


__all__ = [
    "log_actor_choice",
    "log_advisor_choice",
    "log_tool_output",
    "log_review",
    "log_warning",
    "log_advisor_choosing",
    "log_system",
]