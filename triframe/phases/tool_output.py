"""Phase for handling tool operation output"""

import json
import sys
from functools import partial
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List

sys.path.append(str(Path(__file__).parent.parent.parent))

from type_defs import Node, Option, StateRequest, triframeState
from type_defs.operations import (
    BashOutput,
    PythonOutput,
    ScoreLogEntry,
    ScoreOutput,
    SubmissionOutput,
)
from utils import run_phase
from utils.logging import log_tool_output


def enforce_output_limit(output_limit: int, output: str) -> str:
    if len(output) > output_limit:
        half = output_limit // 2
        starts_with = output[:half]
        ends_with = output[-half:]
        return dedent(
            f"""This output was too long to include in its entirety.
        The start and end of the output are shown below.
        {starts_with}
        [output truncated]
        {ends_with}"""
        )
    return output


def format_tool_output(output_limit: int, operation_result: Dict[str, Any]) -> str:
    enforce_limit = partial(enforce_output_limit, output_limit)

    if isinstance(operation_result, BashOutput):
        parts = []
        parts.append(enforce_limit(operation_result.stdout))
        if operation_result.stderr:
            parts.append(f"Error: {enforce_limit(operation_result.stderr)}")
        if operation_result.status and operation_result.status != 0:
            parts.append(f"Exit code: {operation_result.status}")
        return "\n".join(parts)
    elif isinstance(operation_result, PythonOutput):
        parts = [enforce_limit(operation_result.output)]
        if operation_result.error:
            parts.append(f"Error: {enforce_limit(operation_result.error)}")
        return "\n".join(parts)
    elif isinstance(operation_result, ScoreOutput):
        return enforce_limit(str(operation_result.message))
    elif isinstance(operation_result, List[ScoreLogEntry]):
        entries = []
        for entry in operation_result:
            entries.append(entry.model_dump())
        return enforce_limit("\n---\n".join(entries))
    else:
        return enforce_limit(json.dumps(operation_result))


def create_phase_request(state: triframeState) -> List[StateRequest]:
    last_update = state.previous_results[-1]
    # find any tool ops in the last update
    tool_result = next(
        (
            op
            for op in last_update
            if op.type in ["bash", "python", "submit", "score", "score_log"]
        ),
        None,
    )
    if not tool_result:
        raise ValueError("No tool operation found in last update")
    operation_result = tool_result.result
    formatted_output = format_tool_output(state.output_limit, operation_result)
    name = ""
    if isinstance(operation_result, BashOutput):
        name = "run_bash"
    elif isinstance(operation_result, PythonOutput):
        name = "run_python"
    elif isinstance(operation_result, SubmissionOutput):
        name = "submit"
    elif isinstance(operation_result, ScoreOutput):
        name = "score"
    elif isinstance(operation_result, List[ScoreLogEntry]):
        name = "score_log"
    else:
        raise ValueError(f"Unknown tool operation type: {tool_result.type}")
    new_node = Node(
        source="tool_output", options=[Option(content=formatted_output, name=name)]
    )
    state.nodes.append(new_node)
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
