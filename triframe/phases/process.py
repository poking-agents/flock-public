import json
import sys
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).parent.parent.parent))
from triframe.logging import log_actor_choice
from triframe.phases.advisor_ratings import validate_function_call
from type_defs.base import Node, Option
from type_defs.operations import (
    BaseOperationRequest,
    BashParams,
    BashRequest,
    OperationMetadata,
    PythonParams,
    PythonRequest,
    ScoreLogParams,
    ScoreLogRequest,
    ScoreParams,
    ScoreRequest,
    SubmissionParams,
    SubmissionRequest,
)
from type_defs.phases import StateRequest
from type_defs.states import triframeState
from utils.logging import log_warning
from utils.phase_utils import get_last_completion, get_last_function_call, run_phase


def create_phase_request(state: triframeState) -> List[StateRequest]:
    directly_from_actor = any(
        result.type == "generate" for result in state.previous_results[-1]
    )
    if directly_from_actor:
        completion = get_last_completion(state.previous_results[-1])
        function_call = get_last_function_call(state.previous_results[-1])
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
    if validate_function_call(function_call):
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
        if tool_name == "submit":
            tool_operation = SubmissionRequest(
                type="submit",
                params=SubmissionParams(submission=tool_args["answer"]),
                metadata=metadata,
            )
            next_phase = None
        elif tool_name == "run_bash":
            tool_operation = BashRequest(
                type="bash",
                params=BashParams(command=tool_args["command"]),
                metadata=metadata,
            )
        elif tool_name == "run_python":
            tool_operation = PythonRequest(
                type="python",
                params=PythonParams(code=tool_args["code"]),
                metadata=metadata,
            )
        elif tool_name == "score":
            tool_operation = ScoreRequest(
                type="score", params=ScoreParams(), metadata=metadata
            )
        elif tool_name == "score_log":
            tool_operation = ScoreLogRequest(
                type="score_log", params=ScoreLogParams(), metadata=metadata
            )
        elif tool_name == "set_timeout":
            try:
                state.timeout = int(tool_args["timeout"])
                state.nodes.append(
                    Node(
                        source="tool_output",
                        options=[
                            Option(
                                content=f"Timeout set to {state.timeout}",
                                name="set_timeout",
                            )
                        ],
                    )
                )
            except (KeyError, ValueError):
                state.nodes.append(
                    Node(
                        source="warning",
                        options=[
                            Option(
                                content=(
                                    "Invalid set_timeout function call, "
                                    f"timeout remains {state.timeout} seconds"
                                )
                            )
                        ],
                    )
                )
            state.update_usage()
            next_phase = "triframe/phases/advisor.py"
        else:
            raise ValueError(f"Unknown function: {tool_name}")
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
