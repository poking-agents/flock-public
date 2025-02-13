import json
import sys
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).parent.parent.parent))
from triframe.logging import log_actor_choice
from triframe.phases.advisor_ratings import validate_triframe_function_call
from type_defs.base import Node, Option
from type_defs.operations import (
    BaseOperationRequest,
    OperationMetadata,
)
from type_defs.phases import StateRequest
from type_defs.states import triframeState
from utils.functions import create_standard_tool_operation, handle_set_timeout
from utils.logging import log_warning
from utils.phase_utils import get_last_completion, get_last_function_call, run_phase


def create_phase_request(state: triframeState) -> List[StateRequest]:
    directly_from_actor = any(
        result.type == "generate" for result in state.previous_results[-1]
    )
    if directly_from_actor:
        completion = get_last_completion(
            state, state.previous_results[-1], state.settings.enable_tool_use
        )
        function_call = get_last_function_call(
            state, state.previous_results[-1], state.settings.enable_tool_use
        )
        state.nodes.append(
            Node(
                source="actor_choice",
                options=[Option(content=completion, function_call=function_call)],
            )
        )
    else:
        actor_choice = next(
            (node for node in reversed(state.nodes) if node.source == "actor_choice"),
            None,
        )
        if not actor_choice:
            raise ValueError("No actor choice found")
        completion = actor_choice.options[0].content
        function_call = actor_choice.options[0].function_call
    if validate_triframe_function_call(function_call):
        if not isinstance(function_call, dict):
            print(function_call)
            raise ValueError(
                f"Expected function_call to be a dict, got {type(function_call)}"
            )
        tool_name = function_call.get("name")
        tool_args = function_call.get("arguments")
        assert tool_name and tool_args, "Function call must have name and arguments"
        assert isinstance(tool_args, str), "Arguments must be a string"
        tool_args = json.loads(tool_args)
        tool_operation: BaseOperationRequest | None = None
        next_phase = "triframe/phases/tool_output.py"
        metadata = OperationMetadata(
            purpose="tool_execution", phase="process", state_id=state.id
        )

        if tool_name == "set_timeout":
            state = handle_set_timeout(state, tool_args)
            next_phase = "triframe/phases/advisor.py"
        else:
            tool_operation = create_standard_tool_operation(
                tool_name, tool_args, metadata
            )
            if tool_operation is None:
                raise ValueError(f"Unknown function: {tool_name}")

            # Special case for submit operation
            if tool_name == "submit":
                next_phase = None

        operations = []
        if directly_from_actor:
            operations.append(
                log_actor_choice(
                    Option(content=completion, function_call=function_call)
                )
            )
        if tool_operation:
            operations.append(tool_operation)

        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=operations,
                next_phase=next_phase,
            )
        ]
    else:
        log_completion = log_actor_choice(Option(content=completion))
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
                state_model="type_defs.states.triframeState",
                operations=[
                    log_completion,
                    log_warning("No valid function call found in response"),
                ],
                next_phase="triframe/phases/advisor.py",
            )
        ]


if __name__ == "__main__":
    run_phase("process", create_phase_request, "type_defs.states.triframeState")
