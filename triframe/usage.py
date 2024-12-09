from typing import List

from type_defs.operations import (
    BaseOperationRequest,
    BaseOperationResult,
    GetUsageParams,
    GetUsageRequest,
)
from type_defs.states import triframeState


def has_generation_requests(operations: List[BaseOperationRequest]) -> bool:
    """Check if there are any generation requests in the operations list"""
    return any(op.type == "generate" for op in operations)


def add_usage_request(
    operations: List[BaseOperationRequest],
) -> List[BaseOperationRequest]:
    usage_request = GetUsageRequest(
        type="get_usage",
        params=GetUsageParams(),
    )
    return [*operations, usage_request]


def update_state_usage(
    state: triframeState, results: List[BaseOperationResult]
) -> None:
    """Update state usage from get_usage results"""
    usage_result = next((r for r in results if r.type == "get_usage"), None)
    if not usage_result:
        return

    usage = usage_result.result.usage
    # Update state usage
    state.token_usage = usage.tokens
    state.actions_usage = usage.actions
    state.time_usage = usage.total_seconds

    # Update latest node if it exists
    if state.nodes:
        state.nodes[-1].token_usage = usage.tokens
        state.nodes[-1].actions_usage = usage.actions
        state.nodes[-1].time_usage = usage.total_seconds
