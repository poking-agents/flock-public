"""Handlers for logging operations"""

import json
import os
from datetime import datetime
from typing import Optional

from flock.handlers.base import create_handler
from flock.type_defs.operations import (
    LogOutput,
    LogParams,
    LogWithAttributesOutput,
    LogWithAttributesParams,
)
from flock.type_defs.processing import ProcessingMode


async def log_hooks(params: LogParams, deps: Optional[dict]) -> LogOutput:
    hooks_client = deps["hooks_client"]
    content = params.content

    await hooks_client.log(content)
    timestamp = datetime.utcnow().isoformat()
    return LogOutput(
        status="success", message="Log sent through hooks", timestamp=timestamp
    )


async def log_with_attributes_hooks(
    params: LogWithAttributesParams, deps: Optional[dict]
) -> LogWithAttributesOutput:
    hooks_client = deps["hooks_client"]
    attributes = params.attributes
    content = params.content

    await hooks_client.log_with_attributes(attributes, content)
    timestamp = datetime.utcnow().isoformat()
    return LogWithAttributesOutput(
        status="success",
        message="Attributed log sent through hooks",
        timestamp=timestamp,
        attributes=attributes,
    )


async def log_mock(params: LogParams, deps: Optional[dict]) -> LogOutput:
    timestamp = datetime.utcnow().isoformat()
    content = params.content
    os.makedirs("logs", exist_ok=True)

    log_entry = {
        "content": content,
        "timestamp": timestamp,
        "level": params.level,
    }

    # Write to mock log file
    filename = f"logs/mock_log_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(filename, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    return LogOutput(
        status="success",
        message=f"Log entry saved: {content[:100]}...",
        timestamp=timestamp,
    )


async def log_with_attributes_mock(
    params: LogWithAttributesParams, deps: Optional[dict]
) -> LogWithAttributesOutput:
    timestamp = datetime.utcnow().isoformat()
    content = params.content
    attributes = params.attributes

    os.makedirs("logs", exist_ok=True)

    log_entry = {
        "content": content,
        "timestamp": timestamp,
        "attributes": attributes,
    }

    # Write to mock log file
    filename = f"logs/mock_attributed_log_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(filename, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    return LogWithAttributesOutput(
        status="success",
        message=f"Attributed log entry saved: {content[:100]}...",
        timestamp=timestamp,
        attributes=attributes,
    )


handlers = {
    ProcessingMode.HOOKS: create_handler("log", log_hooks),
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("log", log_mock),
}

attributed_handlers = {
    ProcessingMode.HOOKS: create_handler(
        "log_with_attributes", log_with_attributes_hooks
    ),
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler(
        "log_with_attributes", log_with_attributes_mock
    ),
}
