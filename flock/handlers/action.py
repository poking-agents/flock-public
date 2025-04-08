"""Handlers for action operations"""

from datetime import datetime
from typing import Optional

from flock.handlers.base import create_handler
from flock.logger import logger
from flock.type_defs.operations import (
    ActionOutput,
    ActionParams,
)
from flock.type_defs.processing import ProcessingMode


async def action_hooks(params: ActionParams, deps: Optional[dict]) -> ActionOutput:
    """Action handler for hooks mode"""
    hooks_client = deps["hooks_client"]
    action_type = params.action_type
    parameters = params.parameters
    timestamp = params.timestamp or datetime.utcnow()

    try:
        action_data = {
            "type": action_type,
            "parameters": parameters,
            "timestamp": timestamp.isoformat(),
        }

        await hooks_client.action(action_data)
        return ActionOutput(
            status="success",
            message=f"Action {action_type} sent through hooks",
            action=action_data,
        )
    except Exception as e:
        error_msg = f"Error in hooks action: {str(e)}"
        logger.error(error_msg)
        return ActionOutput(status="error", message=error_msg, action={})


async def action_mock(params: ActionParams, deps: Optional[dict]) -> ActionOutput:
    """Action handler for mock mode"""
    action_type = params.action_type
    parameters = params.parameters
    timestamp = params.timestamp or datetime.utcnow()

    try:
        # Log the mock action
        logger.info(f"Mock action: {action_type}")
        logger.info(f"Parameters: {parameters}")

        action_data = {
            "type": action_type,
            "parameters": parameters,
            "timestamp": timestamp.isoformat(),
            "mock": True,
        }

        return ActionOutput(
            status="success",
            message=f"Mock action {action_type} processed",
            action=action_data,
        )
    except Exception as e:
        error_msg = f"Error in mock action: {str(e)}"
        logger.error(error_msg)
        return ActionOutput(status="error", message=error_msg, action={})


handlers = {
    ProcessingMode.HOOKS: create_handler("action", action_hooks),
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("action", action_mock),
}
