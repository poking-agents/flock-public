"""Process task and usage information from hooks"""

import sys
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).parent.parent.parent))
from type_defs.phases import StateRequest
from type_defs.states import triframeState
from utils.logging import log_system
from utils.phase_utils import (
    require_single_results,
    run_phase,
    set_state_from_task_and_usage_outputs,
)


def create_phase_request(state: triframeState) -> List[StateRequest]:
    [task_result, usage_result] = require_single_results(
        state.previous_results[-1], ["get_task", "get_usage"]
    )
    task_output = task_result.result
    usage_output = usage_result.result
    state = set_state_from_task_and_usage_outputs(state, task_output, usage_output)

    return [
        StateRequest(
            state=state,
            state_model="type_defs.states.triframeState",
            operations=[log_system(task_output.instructions)],
            next_phase="triframe/phases/advisor.py",
        )
    ]


if __name__ == "__main__":
    run_phase(
        "process_task_hooks", create_phase_request, "type_defs.states.triframeState"
    )
