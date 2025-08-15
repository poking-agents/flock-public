import json
from typing import Any, Dict, List

from flock.triframe.context_management import (
    limit_name_and_max,
    tool_output_with_usage,
    trim_content,
)
from flock.triframe.logging import log_advisor_choice
from flock.triframe.templates import ACTOR_FN_PROMPT, ENFORCE_FUNCTION_CALL_PROMPT
from flock.type_defs import Message, Node, Option
from flock.type_defs.operations import (
    GenerationParams,
    GenerationRequest,
    GenerationResult,
)
from flock.type_defs.phases import StateRequest
from flock.type_defs.states import triframeState
from flock.utils.functions import (
    combine_function_call_and_content,
    get_standard_completion_function_definitions,
    get_standard_function_definitions,
    parse_completions_function_call,
    remove_code_blocks,
)
from flock.utils.logging import log_warning
from flock.utils.phase_utils import (
    add_dummy_user_message,
    add_usage_request,
    append_thinking_blocks_to_messages,
    get_thinking_blocks,
    run_phase,
)

CLAUDE_THINKING_MODELS = (
    "claude-3-7-sonnet-20250219",
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "claude-opus-4-1-20250805"
)


def non_empty_option_content(option: Option) -> str:
    content = option.content
    if content == "":
        content = "_"
    return content


def prepare_history_for_actor(
    state: triframeState, first_message: Message, include_advice: bool = True
) -> List[Message]:
    messages = []
    current_length = 0
    buffer = 10000
    character_budget = (
        state.context_trimming_threshold - len(first_message.content) - buffer
    )
    for node in reversed(state.nodes):
        message = None
        if node.source in ["advisor_choice", "actor_choice", "tool_output", "warning"]:
            option = node.options[0]
            if node.source == "advisor_choice" and include_advice:
                completion = option.content
                try:
                    tool_use = json.loads(option.function_call["arguments"])["advice"]
                except Exception:
                    tool_use = ""
                if completion == "" and tool_use == "":
                    continue
                advice = ""
                if completion != "" and tool_use != "":
                    advice = f"{completion}\n{tool_use}"
                elif completion != "":
                    advice = completion
                elif tool_use != "":
                    advice = tool_use
                message = Message(
                    content=f"<advisor>\n{advice}\n</advisor>",
                    role="user",
                )
            elif node.source == "actor_choice":
                if state.settings.enable_tool_use:
                    message = Message(
                        content=non_empty_option_content(option),
                        function_call=option.function_call,
                        role="assistant",
                    )
                else:
                    message = Message(
                        content=combine_function_call_and_content(
                            state, option.function_call, option.content
                        ),
                        role="assistant",
                    )
            elif node.source == "tool_output":
                message = Message(
                    content=tool_output_with_usage(state, node),
                    name=option.name,
                    role="function" if state.settings.enable_tool_use else "user",
                )
            elif node.source == "warning":
                message = Message(
                    content=option.content,
                    role="system",
                )
            limit = state.output_limit
            if message:
                if len(message.content) > limit:
                    message.content = trim_content(message.content, limit)
                if current_length + len(message.content) > character_budget:
                    break
                messages.append(message)
                messages = append_thinking_blocks_to_messages(
                    messages, option.thinking_blocks
                )
                current_length += len(message.content)
    for message in messages:
        if message.role == "function" and not message.name:
            raise ValueError("Function messages must have a name")
    # reverse the messages so that they are in the correct order
    ordered_messages = list(reversed(messages))
    # check that the 1st message is not a role="function" message
    # (those must be preceded by a function call message)
    if ordered_messages and ordered_messages[0].role == "function":
        ordered_messages[0] = Message(
            content="The history of the agent's actions has been trimmed.",
            role="system",
        )
    if state.settings.actors[0].model in CLAUDE_THINKING_MODELS:
        ordered_messages = add_dummy_user_message(ordered_messages)

    return ordered_messages


def maybe_function_call(
    res: GenerationResult, keys: List[str]
) -> Dict[str, Any] | None:
    function_call = res.result.outputs[0].function_call
    if not function_call:
        return None
    function_call = json.loads(function_call)
    return {key: function_call[key] for key in keys if key in function_call}


def create_phase_request(state: triframeState) -> List[StateRequest]:
    # Process all advisor outputs from previous results
    operations = []
    advisor_outputs = []
    for result in state.previous_results[-1]:
        if result.type == "generate":
            thinking_blocks = get_thinking_blocks(result.result.outputs[0])
            completion = result.result.outputs[0].completion
            function_call = None
            if state.settings.enable_tool_use:
                function_call = result.result.outputs[0].function_call
            else:
                function_call = parse_completions_function_call(
                    state.settings.enable_xml,
                    ["advise"],
                    completion,
                    {"advise": ("advice", str)},
                )
                if function_call:
                    completion = remove_code_blocks(state, completion)
            advisor_outputs.append((completion, function_call, thinking_blocks))

    for completion, function_call, thinking_blocks in advisor_outputs:
        log_request = log_advisor_choice(
            Option(
                content=completion,
                function_call=function_call,
                thinking_blocks=thinking_blocks,
            )
        )
        operations.append(log_request)
        if completion == "" and function_call is None:
            operations.append(
                log_warning("Advisor output is empty. Not adding to the state")
            )
        elif function_call is None:
            operations.append(
                log_warning(
                    "Advisor output does not contain a valid advise function call. "
                    "Not adding to the state"
                )
            )
        else:
            state.nodes.append(
                Node(
                    source="advisor_choice",
                    options=[
                        Option(
                            content=completion,
                            function_call=function_call,
                            thinking_blocks=thinking_blocks,
                        )
                    ],
                )
            )

    state.update_usage()
    limit_name, limit_max = limit_name_and_max(state)
    content = (ACTOR_FN_PROMPT).format(
        task=state.task_string,
        limit_name=limit_name,
        limit_max=limit_max,
        functions=(
            get_standard_function_definitions(state)
            if state.settings.enable_tool_use
            else get_standard_completion_function_definitions(state)
        ),
    )
    if not state.settings.enable_tool_use:
        content += ENFORCE_FUNCTION_CALL_PROMPT
    first_message = Message(
        role="system",
        content=content,
    )

    # Create separate message lists for with and without advice
    messages_with_advice = [first_message]
    messages_with_advice.extend(
        prepare_history_for_actor(state, first_message, include_advice=True)
    )

    messages_without_advice = [first_message]
    messages_without_advice.extend(
        prepare_history_for_actor(state, first_message, include_advice=False)
    )

    for actor_settings in state.settings.actors:
        params = GenerationParams(
            messages=[msg.model_dump() for msg in messages_with_advice],
            settings=actor_settings,
            functions=(
                get_standard_function_definitions(state)
                if state.settings.enable_tool_use
                else None
            ),
        )
        generation_request = GenerationRequest(type="generate", params=params)
        operations.append(generation_request)
        without_advice_params = GenerationParams(
            messages=[msg.model_dump() for msg in messages_without_advice],
            settings=actor_settings,
            functions=(
                get_standard_function_definitions(state)
                if state.settings.enable_tool_use
                else None
            ),
        )
        generation_request_without_advice = GenerationRequest(
            type="generate", params=without_advice_params
        )
        operations.append(generation_request_without_advice)

    operations = add_usage_request(operations)
    return [
        StateRequest(
            state=state,
            state_model="type_defs.states.triframeState",
            operations=operations,
            next_phase="triframe/phases/advisor_ratings.py",
        )
    ]


if __name__ == "__main__":
    run_phase("actor", create_phase_request, "type_defs.states.triframeState")
