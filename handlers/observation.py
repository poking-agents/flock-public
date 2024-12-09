"""Handlers for observation operations"""

from datetime import datetime
from typing import Optional

from handlers.base import create_handler
from logger import logger
from type_defs.operations import (
    ObservationOutput,
    ObservationParams,
)
from type_defs.processing import ProcessingMode


async def observation_hooks(
    params: ObservationParams, deps: Optional[dict]
) -> ObservationOutput:
    """Observation handler for hooks mode"""
    hooks_client = deps["hooks_client"]
    observation_type = params.observation_type
    content = params.content
    timestamp = params.timestamp or datetime.utcnow()

    try:
        observation_data = {
            "type": observation_type,
            "content": content,
            "timestamp": timestamp.isoformat(),
        }

        await hooks_client.observation(observation_data)
        return ObservationOutput(
            status="success",
            message=f"Observation {observation_type} sent through hooks",
            observation=observation_data,
        )
    except Exception as e:
        error_msg = f"Error in hooks observation: {str(e)}"
        logger.error(error_msg)
        return ObservationOutput(status="error", message=error_msg, observation={})


async def observation_mock(
    params: ObservationParams, deps: Optional[dict]
) -> ObservationOutput:
    """Observation handler for mock mode"""
    observation_type = params.observation_type
    content = params.content
    timestamp = params.timestamp or datetime.utcnow()

    try:
        # Log the mock observation
        logger.info(f"Mock observation: {observation_type}")
        logger.info(f"Content: {content}")

        observation_data = {
            "type": observation_type,
            "content": content,
            "timestamp": timestamp.isoformat(),
            "mock": True,
        }

        return ObservationOutput(
            status="success",
            message=f"Mock observation {observation_type} processed",
            observation=observation_data,
        )
    except Exception as e:
        error_msg = f"Error in mock observation: {str(e)}"
        logger.error(error_msg)
        return ObservationOutput(status="error", message=error_msg, observation={})


handlers = {
    ProcessingMode.HOOKS: create_handler("observation", observation_hooks),
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("observation", observation_mock),
}
