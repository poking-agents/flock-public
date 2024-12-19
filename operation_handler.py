"""Operation handling and orchestration"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from handlers import get_handler
from middleman_client import post_completion
from observation_simulator import create_simulator
from type_defs.operations import (
    RESULT_MODELS,
    OperationRequest,
    OperationResult,
)
from type_defs.processing import ProcessingMode


def setup_dependencies(mode: ProcessingMode) -> Dict[str, Any]:
    deps = {}
    if mode in [ProcessingMode.MIDDLEMAN_SIMULATED]:
        deps["post_completion"] = (
            lambda messages, model="gpt-4o-mini", temp=1.0, n=1, function_call=None, functions=None: post_completion(
                messages=messages,
                model=model,
                temp=temp,
                n=n,
                function_call=function_call,
                functions=functions,
            )
        )
        deps["simulator"] = create_simulator()
    if mode in [ProcessingMode.HOOKS]:
        try:
            from pyhooks import CommonEnvs, Hooks

            deps["hooks_client"] = Hooks(envs=CommonEnvs.from_env())
        except ImportError:
            if mode == ProcessingMode.HOOKS:
                raise ImportError("pyhooks required for HOOKS mode")
    return deps


async def handle_operation(
    request: OperationRequest,
    mode: ProcessingMode,
    dependencies: Dict[str, Any],
    phase: Optional[str] = None,
    state_id: Optional[str] = None,
) -> Tuple[OperationRequest, OperationResult]:
    """Handle a single operation request"""
    handler = get_handler(request.type, mode, dependencies)
    output = await handler(request.params, dependencies)

    result_model = RESULT_MODELS.get(request.type)
    if not result_model:
        raise ValueError(f"Unknown result model for operation type: {request.type}")

    result = result_model(
        type=request.type, result=output, metadata=request.metadata, error=None
    )

    if mode != ProcessingMode.HOOKS:
        try:
            from operations_ui import add_operation_event

            add_operation_event(
                {
                    "state_id": state_id or "unknown",
                    "phase": phase or "unknown_phase",
                    "operation": request.model_dump(),
                    "result": result.model_dump(),
                    "status": "success" if not result.error else "error",
                    "timestamp": time.time(),
                }
            )
        except ImportError:
            pass  # UI not available, skip event

    return request, result


async def handle_operations(
    mode: ProcessingMode,
    operations: List[OperationRequest],
    state_id: Optional[str] = None,
    current_phase: Optional[str] = None,
) -> List[Tuple[OperationRequest, OperationResult]]:
    dependencies = setup_dependencies(mode)
    # Add state_id to dependencies for UI events
    dependencies["state_id"] = state_id or "unknown"

    # Find usage request if present
    usage_op = next((op for op in operations if op.type == "get_usage"), None)
    other_ops = [op for op in operations if op.type != "get_usage"]

    # Handle non-usage operations first
    results = await asyncio.gather(
        *[
            handle_operation(
                request=op,
                mode=mode,
                dependencies=dependencies,
                phase=current_phase,
                state_id=state_id,
            )
            for op in other_ops
        ]
    )

    # Handle usage operation if present
    if usage_op:
        usage_result = await handle_operation(
            request=usage_op,
            mode=mode,
            dependencies=dependencies,
            phase=current_phase,
            state_id=state_id,
        )
        results.append(usage_result)

    return results
