import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

sys.path.append(str(Path(__file__).parent.parent.parent))
from triframe.logging import log_actor_choice, log_system, log_warning
from type_defs.base import Node, Option
from type_defs.operations import (
    BaseOperationRequest,
    BashParams,
    BashRequest,
    OperationMetadata,
    ScoreLogParams,
    ScoreLogRequest,
    ScoreParams,
    ScoreRequest,
    SubmissionParams,
    SubmissionRequest,
)
from type_defs.phases import StateRequest
from type_defs.states import triframeState
from utils.phase_utils import get_last_completion, get_last_function_call, run_phase
from utils.state import save_state


def setup_subagent_state(
    parent_state: triframeState,
    agent_id: str,
    task: str,
    approach: str,
    include_task_description: bool,
    settings=None,
) -> triframeState:
    """Create initial state for a subagent"""
    agent_dir = Path("subagents") / agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    task_string = (
        f"""Another agent is working on this high-level task: <high-level>{parent_state.task_string}</high-level>

Your specific task is:
{task}

Note: You have a dedicated working directory at {agent_dir} to help avoid conflicts with other agents.
You can use this directory for any files you need to create, but you're free to work in other directories if needed."""
        if include_task_description
        else f"""{task}

Note: You have a dedicated working directory at {agent_dir} to help avoid conflicts with other agents.
You can use this directory for any files you need to create, but you're free to work in other directories if needed."""
    )
    subagent_state = triframeState(
        id=agent_id,
        task_string=task_string,
        settings=settings or parent_state.settings,
        previous_results=[],
        nodes=[],
        token_limit=parent_state.token_limit // 2,
        actions_limit=parent_state.actions_limit // 2,
        time_limit=parent_state.time_limit // 2,
        token_usage=0,
        actions_usage=0,
        time_usage=0,
        timeout=parent_state.timeout,
        context_trimming_threshold=parent_state.context_trimming_threshold,
        output_limit=parent_state.output_limit,
        subagent_config={
            "approach": approach,
            "parent_id": parent_state.id,
            "created_at": datetime.now().isoformat(),
        },
        status="initialized",
    )
    return subagent_state


def create_phase_request(state: triframeState) -> List[StateRequest]:
    """Process the latest actor output"""
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
    if not function_call:
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
    tool_name = function_call.get("name")
    tool_args = function_call.get("arguments")
    if not tool_name or not tool_args:
        raise ValueError("Function call must have name and arguments")
    if not isinstance(tool_args, str):
        raise ValueError("Arguments must be a string")
    tool_args = json.loads(tool_args)
    if tool_name == "launch_subagents":
        agents = tool_args["agents"]
        state_requests = []
        for i, agent_spec in enumerate(agents):
            agent_id = f"agent_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            subagent_state = setup_subagent_state(
                parent_state=state,
                agent_id=agent_id,
                task=agent_spec["task"],
                approach=agent_spec["approach"],
                include_task_description=agent_spec["include_task_description"],
            )
            save_state(agent_id, subagent_state)
            state.add_subagent(
                agent_id=agent_id,
                task=agent_spec["task"],
                approach=agent_spec["approach"],
                include_task_description=agent_spec["include_task_description"],
            )
            state_requests.append(
                StateRequest(
                    state=subagent_state,
                    state_model="type_defs.states.triframeState",
                    operations=[],
                    next_phase="triframe/phases/advisor.py",
                )
            )
        task_groups = {}
        for agent in state.active_subagents:
            task_groups.setdefault(agent["task"], []).append(agent["id"])
        for task, agents in task_groups.items():
            task_hash = str(abs(hash(task)) % 10000)
            tournament_id = (
                f"tournament_{task_hash}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            state.start_new_tournament(agents, task, tournament_id)
        state_requests.append(
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=[log_system(f"Launched {len(agents)} subagents")],
                next_phase="triframe/phases/subagents_monitor.py",
            )
        )
        return state_requests
    if tool_name == "conclude":
        if state.is_subagent():
            state.status = "concluded"
            state.nodes.append(
                Node(
                    source="tool_output",
                    options=[
                        Option(
                            content=f"Subagent concluded: {tool_args.get('result', 'No result provided')}",
                            name="conclude",
                        )
                    ],
                )
            )
            return [
                StateRequest(
                    state=state,
                    state_model="type_defs.states.triframeState",
                    operations=[],
                    next_phase=None,
                )
            ]
        else:
            return [
                StateRequest(
                    state=state,
                    state_model="type_defs.states.triframeState",
                    operations=[log_warning("Only subagents can use conclude")],
                    next_phase="triframe/phases/advisor.py",
                )
            ]
    tool_operation: Optional[BaseOperationRequest] = None
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
        bash_params = BashParams(
            command=tool_args["command"],
            agent_id=state.id if state.is_subagent() else None,
        )
        tool_operation = BashRequest(type="bash", params=bash_params, metadata=metadata)
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
            return [
                StateRequest(
                    state=state,
                    state_model="type_defs.states.triframeState",
                    operations=[],
                    next_phase="triframe/phases/advisor.py",
                )
            ]
        except (KeyError, ValueError):
            state.nodes.append(
                Node(
                    source="warning",
                    options=[
                        Option(
                            content=f"Invalid set_timeout function call, timeout remains {state.timeout} seconds"
                        )
                    ],
                )
            )
            return [
                StateRequest(
                    state=state,
                    state_model="type_defs.states.triframeState",
                    operations=[log_warning("Invalid set_timeout arguments")],
                    next_phase="triframe/phases/advisor.py",
                )
            ]
    else:
        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=[log_warning(f"Unknown function: {tool_name}")],
                next_phase="triframe/phases/advisor.py",
            )
        ]
    operations = []
    if directly_from_actor:
        operations.append(
            log_actor_choice(Option(content=completion, function_call=function_call))
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


if __name__ == "__main__":
    run_phase("process", create_phase_request, "type_defs.states.triframeState")
