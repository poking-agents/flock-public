import json
from typing import List

from flock.triframe.context_management import limit_name_and_max, tool_output_with_usage
from flock.triframe.functions import get_advise_function
from flock.triframe.templates import ADVISOR_FN_PROMPT
from flock.type_defs import Message
from flock.type_defs.operations import GenerationParams, GenerationRequest
from flock.type_defs.phases import StateRequest
from flock.type_defs.states import triframeState
from flock.utils.functions import (
    get_standard_completion_function_definitions,
    get_standard_function_definitions,
)
from flock.utils.phase_utils import (
    add_usage_request,
    append_thinking_blocks_to_messages,
    run_phase,
)


def advisor_fn_messages(state: triframeState) -> List[Message]:
    limit_name, limit_max = limit_name_and_max(state)
    messages: List[Message] = [
        Message(
            role="system",
            content=ADVISOR_FN_PROMPT.format(
                task=state.task_string,
                limit_name=limit_name,
                limit_max=limit_max,
                functions=(
                    json.dumps(get_standard_function_definitions(state))
                    if state.settings.enable_tool_use
                    else get_standard_completion_function_definitions(state)
                ),
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
                role="user",
                content=(
                    f"{node.options[0].content}\n"
                    f"Executed Function Call: "
                    f"{json.dumps(node.options[0].function_call)}"
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
            reversed_messages = append_thinking_blocks_to_messages(
                reversed_messages, node.options[0].thinking_blocks
            )
            current_length += len(message.content)
    messages.extend(reversed(reversed_messages))
    if not state.settings.enable_tool_use:
        if state.settings.enable_xml:
            messages.append(
                Message(
                    role="user",
                    content="Now, call the advise tool by strictly following the format"
                    " below with your advise to the agent (do not include the square "
                    "brackets).\n<advise>\n[your advise to the agent]\n</advise>",
                )
            )
        else:
            messages.append(
                Message(
                    role="user",
                    content="Now, call the advise tool by strictly following the format"
                    " below with your advise to the agent (do not include the square "
                    "brackets).\n```advise\n[your advise to the agent]\n```",
                )
            )
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
    dict_messages = [message.model_dump() for message in messages]
    operations = []

    for advisor_settings in state.settings.advisors:
        if state.settings.enable_tool_use:
            # FIXME: the manifest never sets require_function_call to True
            if state.settings.require_function_call:
                advisor_settings.function_call = {"name": "advise"}
            functions = [get_advise_function()]
        else:
            functions = None

        params = GenerationParams(
            messages=dict_messages,
            settings=advisor_settings,
            functions=functions,
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
