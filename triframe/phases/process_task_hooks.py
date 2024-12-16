"""Process task and usage information from hooks"""

import sys
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).parent.parent.parent))
from triframe.logging import log_system
from type_defs.phases import StateRequest
from type_defs.states import triframeState
from utils.phase_utils import require_single_results, run_phase


def create_phase_request(state: triframeState) -> List[StateRequest]:
    [task_result, usage_result] = require_single_results(
        state.previous_results[-1], ["get_task", "get_usage"]
    )
    if task_result.result.scoring.intermediate:
        state.settings.intermediate_scoring = True
    task_output = task_result.result
    usage_output = usage_result.result
    # TODO: remove nudge
    instructions = f"""{task_output.instructions}
Use subagents to help you complete this task"""
    log_task_operation = log_system(task_output.instructions)
    state.task_string = task_output.instructions
    state.scoring = task_output.scoring.model_dump()
    state.token_limit = usage_output.usageLimits.tokens
    state.actions_limit = usage_output.usageLimits.actions
    state.time_limit = usage_output.usageLimits.total_seconds
    return [
        StateRequest(
            state=state,
            state_model="type_defs.states.triframeState",
            operations=[log_task_operation],
            next_phase="triframe/phases/advisor.py",
        )
    ]


if __name__ == "__main__":
    run_phase(
        "process_task_hooks", create_phase_request, "type_defs.states.triframeState"
    )
