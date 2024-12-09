"""Base handler definitions and utilities"""

import json
import sys
from typing import Awaitable, Callable, Optional, Protocol, TypeVar

from logger import logger
from type_defs.operations import (
    ActionRequest,
    BaseOperationRequest,
    BashRequest,
    GenerationRequest,
    GetTaskRequest,
    GetUsageRequest,
    LogRequest,
    LogWithAttributesRequest,
    ObservationRequest,
    PythonRequest,
    ReadMessagesRequest,
    SaveStateRequest,
    ScoreLogRequest,
    ScoreRequest,
    SubmissionRequest,
    WriteMessageRequest,
)
from type_defs.processing import ProcessingMode

OPERATION_REQUEST_MAP = {
    "log": LogRequest,
    "bash": BashRequest,
    "python": PythonRequest,
    "generate": GenerationRequest,
    "submit": SubmissionRequest,
    "log_with_attributes": LogWithAttributesRequest,
    "action": ActionRequest,
    "observation": ObservationRequest,
    "get_usage": GetUsageRequest,
    "get_task": GetTaskRequest,
    "save_state": SaveStateRequest,
    "score": ScoreRequest,
    "score_log": ScoreLogRequest,
    "write_message": WriteMessageRequest,
    "read_messages": ReadMessagesRequest,
}
ParamsT = TypeVar("ParamsT")
OutputT = TypeVar("OutputT")


class OperationHandler(Protocol[ParamsT, OutputT]):
    """Protocol for operation handlers"""

    async def __call__(self, params: ParamsT, dependencies: Optional[dict]) -> OutputT:
        """Execute the operation"""
        pass


HandlerExecutor = Callable[[ParamsT, Optional[dict]], Awaitable[OutputT]]


def validate_operation_request(
    raw_request: dict, operation_type: str
) -> BaseOperationRequest:
    request_class = OPERATION_REQUEST_MAP.get(operation_type)
    if request_class:
        logger.debug(f"create_handler: request: {json.dumps(raw_request, indent=2)}")
        logger.debug(f"Converting request to {request_class.__name__}")
        request = request_class(**raw_request)
        logger.debug(f"Converted request: {request}")
        return request
    else:
        raise ValueError(f"Unknown operation type: {operation_type}")


def validate_untyped_request(raw_request: dict) -> BaseOperationRequest:
    for operation_type, request_class in OPERATION_REQUEST_MAP.items():
        try:
            return request_class(**raw_request)
        except Exception:
            pass
    raise ValueError(f"Could not validate request: {raw_request}")


def create_handler(
    operation_type: str, executor: HandlerExecutor[ParamsT, OutputT]
) -> OperationHandler[ParamsT, OutputT]:
    """Create a handler with validation and sanitization"""

    class Handler(OperationHandler[ParamsT, OutputT]):
        async def __call__(
            self, params: ParamsT, dependencies: Optional[dict] = None
        ) -> OutputT:
            try:
                return await executor(params, dependencies or {})
            except Exception as e:
                logger.error(f"Error in {operation_type} handler: {str(e)}")
                sys.exit(1)

    return Handler()


def get_handler(
    operation_type: str, mode: ProcessingMode, dependencies: Optional[dict] = None
) -> OperationHandler:
    """Get a handler for the given operation type and mode"""
    from handlers import handler_registry

    if operation_type not in handler_registry:
        raise ValueError(f"Unknown operation type: {operation_type}")
    mode_handlers = handler_registry[operation_type]
    if mode not in mode_handlers:
        raise ValueError(f"No handler found for {operation_type} in mode {mode}")
    return mode_handlers[mode]


OPERATION_REQUEST_MAP = {
    "log": LogRequest,
    "bash": BashRequest,
    "python": PythonRequest,
    "generate": GenerationRequest,
    "submit": SubmissionRequest,
    "log_with_attributes": LogWithAttributesRequest,
    "action": ActionRequest,
    "observation": ObservationRequest,
    "get_usage": GetUsageRequest,
    "get_task": GetTaskRequest,
    "save_state": SaveStateRequest,
    "score": ScoreRequest,
    "score_log": ScoreLogRequest,
    "write_message": WriteMessageRequest,
    "read_messages": ReadMessagesRequest,
}
