"""Phase for handling tool operation output"""

from typing import List

from flock.type_defs import ModularState, Node, Option, StateRequest
from flock.utils import run_phase
from flock.utils.functions import (
    format_tool_output,
    get_tool_operation,
)
from flock.utils.logging import log_tool_output


def create_phase_request(state: ModularState) -> List[StateRequest]:
    last_update = state.previous_results[-1]
    operation = get_tool_operation(last_update)
    formatted_output = format_tool_output(state.output_limit, operation.result)
    name = operation.type
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
            state_model="type_defs.states.ModularState",
            operations=[log_request],
            next_phase="modular/phases/prompter.py",
        )
    ]


if __name__ == "__main__":
    run_phase("tool_output", create_phase_request, "type_defs.states.ModularState")
