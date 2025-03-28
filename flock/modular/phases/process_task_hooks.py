"""Process task and usage information from hooks"""

from typing import List

from flock.type_defs.phases import StateRequest
from flock.type_defs.states import ModularState
from flock.utils.logging import log_system
from flock.utils.phase_utils import (
    require_single_results,
    run_phase,
    set_state_from_task_and_usage_outputs,
)


def create_phase_request(state: ModularState) -> List[StateRequest]:
    """Process task and usage information"""
    # Get task and usage results
    [task_result, usage_result] = require_single_results(
        state.previous_results[-1], ["get_task", "get_usage"]
    )
    if task_result.result.scoring.intermediate:
        state.settings.intermediate_scoring = True
    task_output = task_result.result
    usage_output = usage_result.result
    state = set_state_from_task_and_usage_outputs(state, task_output, usage_output)

    return [
        StateRequest(
            state=state,
            state_model="flock.type_defs.states.ModularState",
            operations=[log_system(task_output.instructions)],
            next_phase="modular/phases/prompter.py",
        )
    ]


if __name__ == "__main__":
    run_phase(
        "process_task_hooks",
        create_phase_request,
        "flock.type_defs.states.ModularState",
    )
