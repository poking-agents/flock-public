import json
from pathlib import Path
from typing import List

from flock.type_defs.operations import (
    GetTaskParams,
    GetTaskRequest,
    GetUsageParams,
    GetUsageRequest,
    MiddlemanSettings,
    OperationMetadata,
)
from flock.type_defs.phases import StateRequest
from flock.type_defs.states import triframeSettings, triframeState
from flock.utils.phase_utils import run_phase


def initialize_state_from_settings(state_id: str, settings_path: str) -> triframeState:
    """Initialize state from settings file"""
    with open(settings_path) as f:
        settings_data = json.load(f)

    print(f"Initializing state from settings file: {settings_path}")
    print(f"Settings data: {json.dumps(settings_data, indent=2)}")

    # Create triframeSettings directly from the settings data
    settings = triframeSettings(
        actors=[
            MiddlemanSettings(**actor) for actor in settings_data.get("actors", [])
        ],
        advisors=[
            MiddlemanSettings(**advisor)
            for advisor in settings_data.get("advisors", [])
        ],
        raters=[
            MiddlemanSettings(**rater) for rater in settings_data.get("raters", [])
        ],
        require_function_call=settings_data.get("require_function_call", False),
        limit_type=settings_data.get("limit_type", "token"),
        intermediate_scoring=settings_data.get("intermediate_scoring", False),
        enable_advising=settings_data.get("enable_advising", True),
        enable_tool_use=settings_data.get("enable_tool_use", True),
        enable_xml=settings_data.get("enable_xml", False),
    )

    initial_state = triframeState(
        id=state_id,
        previous_results=[],
        task_string="",
        scoring={},
        permissions={},
        settings=settings,
        nodes=[],
        token_limit=300000,
        token_usage=0,
        actions_limit=1000,
        actions_usage=0,
        time_limit=604800.0,
        time_usage=0.0,
        timeout=60,
        context_trimming_threshold=80000,
        output_limit=10000,
        max_ops=50,
        ops_count=0,
    )

    print(f"Initialized state for {state_id}")
    return initial_state


def create_phase_request(state: triframeState) -> List[StateRequest]:
    """Create initial phase request"""
    settings_path = state.previous_results[0][0].result.settings_path
    if not settings_path:
        settings_path = f"{state.id}_settings.json"
        print(f"No settings_path provided, using default: {settings_path}")
    if not Path(settings_path).exists():
        raise FileNotFoundError(f"Settings file not found: {settings_path}")

    initial_state = initialize_state_from_settings(state.id, settings_path)

    task_request = GetTaskRequest(
        type="get_task", params=GetTaskParams(), metadata=OperationMetadata()
    )
    usage_request = GetUsageRequest(
        type="get_usage", params=GetUsageParams(), metadata=OperationMetadata()
    )

    return [
        StateRequest(
            state=initial_state,
            state_model="type_defs.states.triframeState",
            operations=[task_request, usage_request],
            next_phase="triframe/phases/process_task_hooks.py",
        )
    ]


if __name__ == "__main__":
    run_phase(
        "init_from_settings", create_phase_request, "type_defs.states.triframeState"
    )
