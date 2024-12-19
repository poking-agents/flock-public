"""Actor phase for modular workflow"""

import json
import sys
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).parent.parent.parent))


from type_defs.base import Node, Option
from type_defs.operations import (
    BaseOperationRequest,
    OperationMetadata,
)
from type_defs.phases import StateRequest
from type_defs.states import ModularState
from utils.functions import (
    create_standard_tool_operation,
    handle_set_timeout,
    validate_function_call,
)
from utils.logging import create_log_request, log_warning
from utils.phase_utils import get_last_completion, run_phase
from utils.styles import log_styles


def create_function_call_log_message(
    completion: str, function_call: dict
) -> tuple[str, dict]:
    """Create log message and determine style for a validated function call
    generated by an actor"""
    message = f"Completion content:\n{completion}\n" if completion else ""
    function_name = function_call["name"]
    message += f"Function called: {function_name}"
    style = log_styles["actor"]

    if function_name not in ["score", "score_log"]:
        try:
            args = json.loads(function_call["arguments"])
            first_key = next(iter(args))
            message += f" with {first_key}:\n{args[first_key]}\n"
        except (json.JSONDecodeError, KeyError, TypeError):
            message += f"Function call does not parse: {function_call}\n"
            style = log_styles["warning"]

    return message, style


def create_phase_request(state: ModularState) -> List[StateRequest]:
    """Create phase request for actor"""
    assert state.nodes[-1].source == "actor_choice"
    function_call = state.nodes[-1].options[0].function_call
    generator_phase_result = state.previous_results[-2]
    completion = get_last_completion(generator_phase_result)

    if not validate_function_call(function_call):
        log_request = create_log_request(completion, log_styles["actor"])
        state.nodes.append(
            Node(
                source="warning",
                options=[
                    Option(content="No valid function call found in the last response")
                ],
            )
        )

        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.ModularState",
                operations=[
                    log_request,
                    log_warning("No valid function call found in response"),
                ],
                next_phase="modular/phases/prompter.py",
            )
        ]

    tool_name = function_call.get("name")
    tool_args = function_call.get("arguments")
    tool_args = json.loads(tool_args)
    tool_operation: BaseOperationRequest | None = None
    metadata = OperationMetadata(
        purpose="tool_execution", phase="actor", state_id=state.id
    )
    next_phase = "modular/phases/tool_output.py"

    # set_timeout doesn't require a tool operation
    if tool_name == "set_timeout":
        state = handle_set_timeout(state, tool_args)
        next_phase = "modular/phases/prompter.py"
    else:
        tool_operation = create_standard_tool_operation(tool_name, tool_args, metadata)
        if not tool_operation:
            raise ValueError(f"Unknown function: {tool_name}")
        next_phase = "modular/phases/tool_output.py" if tool_name != "submit" else None

    message, style = create_function_call_log_message(completion, function_call)
    log_request = create_log_request(message, style)
    operations = [log_request]
    if tool_operation:
        operations.append(tool_operation)
    return [
        StateRequest(
            state=state,
            state_model="type_defs.states.ModularState",
            operations=operations,
            next_phase=next_phase,
        )
    ]


if __name__ == "__main__":
    run_phase("actor", create_phase_request, "type_defs.states.ModularState")
