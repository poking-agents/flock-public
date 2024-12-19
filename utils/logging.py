"""Logging utilities for duet workflow"""

from type_defs.operations import LogWithAttributesParams, LogWithAttributesRequest
from utils.styles import log_styles


def create_log_request(content: str, style: dict) -> LogWithAttributesRequest:
    """Create a log request with the given content and style"""
    return LogWithAttributesRequest(
        type="log_with_attributes",
        params=LogWithAttributesParams(content=content, attributes=style),
    )


def log_tool_output(content: str) -> LogWithAttributesRequest:
    """Log tool output with appropriate styling"""
    return create_log_request(content, log_styles["tool_output"])


def log_warning(content: str) -> LogWithAttributesRequest:
    """Log a warning with appropriate styling"""
    return create_log_request(content, log_styles["warning"])


def log_system(content: str) -> LogWithAttributesRequest:
    """Log system messages with appropriate styling"""
    return create_log_request(content, log_styles["system"])


__all__ = [
    "log_tool_output",
    "log_warning",
    "log_system",
]
