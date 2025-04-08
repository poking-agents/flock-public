"""Actor phase for modular workflow"""

import json
import sys
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).parent.parent.parent))


from flock.type_defs.base import Node, Option
from flock.type_defs.operations import (
    BaseOperationRequest,
    OperationMetadata,
)
from flock.type_defs.phases import StateRequest
from flock.type_defs.states import ModularState
from flock.utils.functions import (
    create_standard_tool_operation,
    handle_set_timeout,
    validate_function_call,
)
from flock.utils.logging import create_log_request, log_warning
from flock.utils.phase_utils import (
    get_last_completion,
    get_last_generator_output,
    run_phase,
)
from flock.utils.styles import standard_log_styles


def create_function_call_log_message(
    completion: str,
    function_call: dict,
    reasoning_completion: str | None,
) -> tuple[str, dict]:
    """Create log message and determine style for a validated function call
    generated by an actor"""
    message_parts = []
    if reasoning_completion:
        message_parts.extend(
            [
                "Thinking:",
                reasoning_completion,
            ]
        )
    message_parts.extend(
        [
            "Completion content:",
            completion,
        ]
    )

    function_name = function_call["name"]
    function_call_message = f"Function called: {function_name}"
    function_call_args = None
    style = standard_log_styles["actor"]

    if function_name not in ["score", "score_log"]:
        try:
            args = json.loads(function_call["arguments"])
            first_key = next(iter(args))
            function_call_message += f" with {first_key}:"
            function_call_args = args[first_key]
        except (json.JSONDecodeError, KeyError, TypeError):
            function_call_args = f"Function call does not parse: {function_call}\n"
            style = standard_log_styles["warning"]

    message_parts.append(function_call_message)
    if function_call_args:
        message_parts.append(json.dumps(function_call_args))
    message = "\n".join(message_parts)
    return message, style


def create_phase_request(state: ModularState) -> List[StateRequest]:
    """Create phase request for actor"""
    assert state.nodes[-1].source == "actor_choice"
    function_call = state.nodes[-1].options[0].function_call
    generator_output = get_last_generator_output(state.previous_results[-2])
    completion = get_last_completion(state, generator_output)

    if not validate_function_call(function_call):
        log_request = create_log_request(completion, standard_log_styles["actor"])
        if function_call:
            # must add tool output block for non empty function call to avoid api errors
            state.nodes.append(
                Node(
                    source="tool_output",
                    options=[Option(content="")],
                )
            )
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
        tool_timeout = state.timeout  # currently only used for bash and python
        tool_operation = create_standard_tool_operation(
            tool_name,
            tool_args,
            metadata,
            tool_timeout,
        )
        if not tool_operation:
            raise ValueError(f"Unknown function: {tool_name}")
        next_phase = "modular/phases/tool_output.py" if tool_name != "submit" else None

    message, style = create_function_call_log_message(
        completion, function_call, generator_output.reasoning_completion
    )
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
