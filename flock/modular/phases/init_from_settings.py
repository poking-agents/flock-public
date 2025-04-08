import json
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
from flock.type_defs.states import ModularSettings, ModularState
from flock.utils.phase_utils import get_settings_path, run_phase


def initialize_state_from_settings(state_id: str, settings_path: str) -> ModularState:
    """Initialize state from settings file"""
    with open(settings_path) as f:
        settings_data = json.load(f)

    print(f"Initializing modular state from settings file: {settings_path}")
    print(f"Settings data: {json.dumps(settings_data, indent=2)}")

    # Create ModularSettings from the settings data
    settings = ModularSettings(
        generator=MiddlemanSettings(**settings_data["generator"]),
        limit_type=settings_data.get("limit_type", "token"),
        intermediate_scoring=settings_data.get("intermediate_scoring", False),
    )

    initial_state = ModularState(
        id=state_id,
        previous_results=[],
        task_string="",
        scoring={},
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
    )

    print(f"Initialized modular state for {state_id}")
    return initial_state


def create_phase_request(state: ModularState) -> List[StateRequest]:
    """Create initial phase request"""
    # Get settings path from first result
    settings_path = get_settings_path(state.id, state.previous_results)
    initial_state = initialize_state_from_settings(state.id, settings_path)

    # Create task and usage requests
    task_request = GetTaskRequest(
        type="get_task",
        params=GetTaskParams(),
        metadata=OperationMetadata(purpose="init", state_id=state.id),
    )
    usage_request = GetUsageRequest(
        type="get_usage",
        params=GetUsageParams(),
        metadata=OperationMetadata(purpose="init", state_id=state.id),
    )

    return [
        StateRequest(
            state=initial_state,
            state_model="type_defs.states.ModularState",
            operations=[task_request, usage_request],
            next_phase="modular/phases/process_task_hooks.py",
        )
    ]


if __name__ == "__main__":
    run_phase(
        "init_from_settings",
        create_phase_request,
        "type_defs.states.ModularState",
    )
