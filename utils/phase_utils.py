"""Utilities for phase handling and execution"""

import asyncio
import importlib
import json
import sys
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
)

import aiohttp
from pydantic import BaseModel, ValidationError

from config import API_BASE_URL
from logger import logger
from type_defs.operations import (
    REQUEST_MODELS,
    RESULT_MODELS,
    BaseOperationRequest,
    BaseOperationResult,
    GetTaskOutput,
    GetUsageOutput,
    GetUsageParams,
    GetUsageRequest,
    OperationResult,
)
from type_defs.phases import PreviousOperations, StateRequest
from type_defs.states import AgentState, BaseState
from utils.state import load_state, save_state

T = TypeVar("T", bound=BaseState)


def get_last_result(
    latest_results: List[OperationResult], operation_type: Optional[str] = None
) -> Optional[OperationResult]:
    if operation_type:
        results = [r for r in latest_results if r[0].type == operation_type]
    return results[-1] if results else None


def get_last_function_call(
    latest_results: List[OperationResult],
) -> Optional[Dict[str, Any]]:
    for res in reversed(latest_results):
        if res.type == "generate":
            outputs = res.result.outputs
            if outputs and outputs[0].function_call:
                return outputs[0].function_call
    return None


def results_of_type(
    latest_results: List[OperationResult], operation_type: str
) -> List[OperationResult]:
    return [result for result in latest_results if result.type == operation_type]


def require_single_results(
    latest_results: List[OperationResult], operation_types: List[str]
) -> List[OperationResult]:
    results = []
    for op_type in operation_types:
        matches = [results for results in latest_results if results.type == op_type]
        if not matches:
            raise ValueError(f"No result found for operation type: {op_type}")
        if len(matches) > 1:
            raise ValueError(f"Multiple results found for operation type: {op_type}")
        results.append(matches[0])
    return results


def validate_operation_request(raw_request: Dict[str, Any]) -> BaseOperationRequest:
    """Validate an operation request using the base model"""
    if not isinstance(raw_request, dict):
        raise ValueError(f"Request must be a dictionary, got {type(raw_request)}")
    try:
        base_request = BaseOperationRequest(**raw_request)
        if base_request.type in REQUEST_MODELS:
            specific_model = REQUEST_MODELS[base_request.type]
            return specific_model(**raw_request)
        return base_request
    except ValidationError as e:
        print(f"Validation error details: {str(e)}")
        raise ValueError(f"Request validation failed:\n{e}")


def validate_operation_result(raw_result: Dict[str, Any]) -> BaseOperationResult:
    """Validate an operation result using the base model"""
    if not isinstance(raw_result, dict):
        raise ValueError(f"Result must be a dictionary, got {type(raw_result)}")
    try:
        base_result = BaseOperationResult(**raw_result)
        if base_result.type in RESULT_MODELS:
            specific_model = RESULT_MODELS[base_result.type]
            return specific_model(**raw_result)
        return base_result
    except ValidationError as e:
        print(f"Validation error details: {str(e)}")
        raise ValueError(f"Result validation failed:\n{e}")


def validate_update_pair(
    update: List[Any], index: int
) -> Tuple[BaseOperationRequest, BaseOperationResult]:
    """Validate a request-result pair"""
    if not isinstance(update, list) or len(update) != 2:
        raise ValueError(f"Update {index} is not a valid request-result pair")
    try:
        req = validate_operation_request(update[0])
        res = validate_operation_result(update[1])
        return req, res
    except Exception as e:
        print(f"Failed to validate update {index}:")
        print(f"Raw update: {json.dumps(update, indent=2)}")
        raise ValueError(f"Invalid update {index}:\n{str(e)}")


def get_last_completion(latest_results: List[OperationResult]) -> str:
    for res in reversed(latest_results):
        if res.type == "generate":
            return res.result.outputs[0].completion


def serialize_for_json(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    elif isinstance(obj, (list, tuple)):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, type):
        return f"{obj.__module__}.{obj.__name__}"
    return obj


def get_model_class(model_path: str) -> Type[BaseModel]:
    """Import and return a model class from its string path"""
    try:
        module_path, class_name = model_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        logger.error(f"Error importing model {model_path}: {str(e)}")
        raise ValueError(f"Model not found: {model_path}")


async def process_request(
    session: aiohttp.ClientSession, req: StateRequest, phase_name: str
) -> aiohttp.ClientResponse:
    """Process a state request"""
    save_state(req.state.id, req.state)
    workflow_data = {
        "state_id": req.state.id,
        "operations": [op.model_dump() for op in req.operations],
        "current_phase": phase_name,
        "next_phase": req.next_phase,
        "delay": req.delay,
    }
    return await session.post(
        f"{API_BASE_URL}/run_workflow",
        json=workflow_data,
        headers={"Content-Type": "application/json"},
    )


def validate_latest_results(previous_operations_raw: Dict[str, Any]) -> Dict[str, Any]:
    if "updates" not in previous_operations_raw:
        raise ValueError("Previous results missing 'updates' field")
    validated_updates = []
    for i, update in enumerate(previous_operations_raw["updates"]):
        req, res = validate_update_pair(update, i)
        validated_updates.append((req, res))
    previous_operations_raw["updates"] = validated_updates
    previous_operations = PreviousOperations(**previous_operations_raw)
    latest_results = [
        req_res[1].model_dump() for req_res in previous_operations.updates
    ]
    return latest_results


async def run_main(
    phase_name: str,
    create_request_func: Callable[[T], List[StateRequest]],
    state_model: str,
) -> None:
    """
    Args:
        phase_name: Name of the current phase
        create_request_func: Function to create the phase requests
        state_model: Fully qualified name of the state model class as string
    """
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "error": f"Usage: python {phase_name}.py <state_id>",
                    "status": "error",
                    "updates": [],
                }
            )
        )
        sys.exit(1)
    try:
        state_id = sys.argv[1]
        previous_operations_raw = json.loads(sys.stdin.read())
        latest_results = validate_latest_results(previous_operations_raw)
        logger.info(f"Starting phase: {phase_name}")
        logger.debug(f"State ID: {state_id}")
        state_dict = load_state(state_id)
        state_dict["previous_results"].append(latest_results)
        state_model_class = get_model_class(state_model)
        current_state = state_model_class(**state_dict)
        state_requests = create_request_func(current_state)
        async with aiohttp.ClientSession() as session:
            tasks = [
                process_request(session, req, phase_name) for req in state_requests
            ]
            if tasks:
                responses = await asyncio.gather(*tasks)
                for response in responses:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Workflow request failed: {error_text}")
                    result = await response.json()
                    logger.debug(f"Workflow response: {result}")
        logger.info(f"Phase {phase_name} completed")
    except Exception:
        logger.error(f"Error in {phase_name}", exc_info=True)
        sys.exit(1)


def run_phase(
    phase_name: str,
    create_request_func: Callable[[T], List[StateRequest]],
    state_model: str,
) -> None:
    asyncio.run(run_main(phase_name, create_request_func, state_model))


def get_settings_path(state_id: str, previous_results) -> str:
    """Get settings path from state or use default"""
    settings_path = previous_results[0][0].result.settings_path
    if not settings_path:
        settings_path = f"{state_id}_settings.json"
        print(f"No settings_path provided, using default: {settings_path}")
    if not Path(settings_path).exists():
        raise FileNotFoundError(f"Settings file not found: {settings_path}")
    return settings_path


def set_state_from_task_and_usage_outputs(
    state: AgentState, task_output: GetTaskOutput, usage_output: GetUsageOutput
) -> AgentState:
    state.task_string = task_output.instructions
    state.scoring = task_output.scoring.model_dump()
    state.token_limit = usage_output.usageLimits.tokens
    state.actions_limit = usage_output.usageLimits.actions
    state.time_limit = usage_output.usageLimits.total_seconds
    return state


def add_usage_request(
    operations: List[BaseOperationRequest],
) -> List[BaseOperationRequest]:
    usage_request = GetUsageRequest(
        type="get_usage",
        params=GetUsageParams(),
    )
    return [*operations, usage_request]
