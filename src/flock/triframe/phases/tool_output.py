"""Phase for handling tool operation output"""

import sys
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).parent.parent.parent))

from type_defs import Node, Option, StateRequest, triframeState
from utils import run_phase
from utils.functions import (
    format_tool_output,
    get_tool_operation_result,
    get_tool_output_name,
)
from utils.logging import log_tool_output


def create_phase_request(state: triframeState) -> List[StateRequest]:
    last_update = state.previous_results[-1]
    operation_result = get_tool_operation_result(last_update)
    formatted_output = format_tool_output(state.output_limit, operation_result)
    name = get_tool_output_name(operation_result)
    state.nodes.append(
        Node(
            source="tool_output", options=[Option(content=formatted_output, name=name)]
        )
    )
    # update the per-step usage in the latest tool_output node
    state.update_usage()
    log_request = log_tool_output(formatted_output)
    return [
        StateRequest(
            state=state,
            state_model="type_defs.states.triframeState",
            operations=[log_request],
            next_phase="triframe/phases/advisor.py",
        )
    ]


if __name__ == "__main__":
    run_phase("tool_output", create_phase_request, "type_defs.states.triframeState")
