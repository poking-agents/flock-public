import json
import sys
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).parent.parent.parent))
from triframe.context_management import limit_name_and_max, tool_output_with_usage
from triframe.functions import get_advise_function
from triframe.templates import ADVISOR_FN_PROMPT
from triframe.usage import add_usage_request
from type_defs import Message
from type_defs.operations import GenerationParams, GenerationRequest
from type_defs.phases import StateRequest
from type_defs.states import triframeState
from utils.functions import get_standard_function_definitions
from utils.phase_utils import run_phase


def advisor_fn_messages(state: triframeState) -> List[Message]:
    limit_name, limit_max = limit_name_and_max(state)
    messages: List[Message] = [
        Message(
            role="system",
            content=ADVISOR_FN_PROMPT.format(
                task=state.task_string,
                limit_name=limit_name,
                limit_max=limit_max,
                functions=json.dumps(get_standard_function_definitions(state)),
            ),
        )
    ]
    first_message_length = len(messages[0].content)
    buffer = 10000
    character_budget = state.context_trimming_threshold - first_message_length - buffer
    current_length = 0
    reversed_messages = []
    for node in reversed(state.nodes):
        if current_length >= character_budget:
            break
        message = None
        if node.source == "actor_choice":
            message = Message(
                role="assistant",
                content=(
                    f"{node.options[0].content} "
                    f"function_call: {json.dumps(node.options[0].function_call)}"
                ),
            )
        elif node.source == "tool_output":
            message = Message(
                role="user",
                content=f"""<{node.options[0].name}-output>
{tool_output_with_usage(state, node)}
</{node.options[0].name}-output>""",
            )
        elif node.source == "warning":
            message = Message(role="system", content=node.options[0].content)
        else:
            continue
        if message:
            limit = state.output_limit
            if len(message.content) > limit:
                half = limit // 2
                message.content = f"""{message.content[:half]}
... [trimmed {len(message.content) - limit} characters] ...
{message.content[-half:]}"""
            if current_length + len(message.content) > character_budget:
                break
            reversed_messages.append(message)
            current_length += len(message.content)
    messages.extend(reversed(reversed_messages))
    return messages


def create_phase_request(state: triframeState) -> List[StateRequest]:
    """Create phase request for advisor"""
    if not state.task_string:
        raise ValueError("No task provided")
    if not state.settings.enable_advising:
        state.update_usage()
        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=[],
                next_phase="triframe/phases/actor.py",
            )
        ]
    state.update_usage()
    messages = advisor_fn_messages(state)
    dict_messages = [message.dict() for message in messages]
    operations = []
    for advisor_settings in state.settings.advisors:
        if state.settings.require_function_call:
            advisor_settings.function_call = {"name": "advise"}
        params = GenerationParams(
            messages=dict_messages,
            settings=advisor_settings,
            functions=[get_advise_function()],
        )
        generation_request = GenerationRequest(type="generate", params=params)
        operations.append(generation_request)
    operations = add_usage_request(operations)
    return [
        StateRequest(
            state=state,
            state_model="type_defs.states.triframeState",
            operations=operations,
            next_phase="triframe/phases/actor.py",
        )
    ]


if __name__ == "__main__":
    run_phase("advisor", create_phase_request, "type_defs.states.triframeState")
