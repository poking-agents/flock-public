"""Prompter phase for modular workflow"""

import sys
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).parent.parent.parent))

import tiktoken

from modular.templates import NOTICE_TRIMMED
from type_defs.base import Message
from type_defs.phases import StateRequest
from type_defs.states import ModularState
from utils.phase_utils import run_phase


def trim_message_list(messages: List[Message], target_tok_length: int) -> List[Message]:
    """Trim messages to fit within token budget while preserving context"""
    enc = tiktoken.get_encoding("cl100k_base")
    tokens_to_use = target_tok_length - len(
        enc.encode(NOTICE_TRIMMED, disallowed_special=())
    )

    # Always keep first 4 messages for context
    for msg in messages[:4]:
        tokens_to_use -= len(enc.encode(msg.content, disallowed_special=()))
        if msg.function_call:
            tokens_to_use -= len(
                enc.encode(str(msg.function_call), disallowed_special=())
            )

    # Try to keep as many recent messages as possible
    tail_messages = []
    for msg in messages[4:][::-1]:
        msg_tokens = len(enc.encode(msg.content, disallowed_special=()))
        if msg.function_call:
            msg_tokens += len(enc.encode(str(msg.function_call), disallowed_special=()))

        if tokens_to_use - msg_tokens < 0:
            break

        tokens_to_use -= msg_tokens
        tail_messages.append(msg)

    if tokens_to_use >= 0:
        return messages

    return (
        messages[:4]
        + [Message(role="system", content=NOTICE_TRIMMED)]
        + tail_messages[::-1]
    )


def prepare_messages(state: ModularState) -> List[Message]:
    """Prepare messages for generation, with context and usage awareness"""
    messages = []
    token_usage_fraction = state.token_usage / state.token_limit
    time_usage_fraction = state.time_usage / state.time_limit

    # Get messages from node history
    for node in state.nodes:
        option = node.options[0]
        if node.source == "tool_output":
            message = Message(
                content=option.content,
                name=option.name,
                role="function",
            )
        else:
            message = Message(
                role="assistant" if option.function_call else "user",
                content=option.content,
                function_call=option.function_call,
                name=option.name,
            )
        messages.append(message)

    # Add usage warning if needed
    if token_usage_fraction > time_usage_fraction:
        usage_fraction = token_usage_fraction
        usage_type = "tokens"
        usage_limit = state.token_limit
    else:
        usage_fraction = time_usage_fraction
        usage_type = "time"
        usage_limit = state.time_limit

    usage_message = (
        "So far in this attempt at the task, you have used "
        f"{usage_fraction:.1%} {usage_type}, out of the total limit of {usage_limit}."
    )
    if usage_fraction > 0.9:
        usage_message += " You should submit a final answer soon."
    elif usage_fraction > 0.75:
        usage_message += " You should attempt to reach a final answer soon."

    messages.append(Message(role="user", content=usage_message))
    messages = trim_message_list(messages, state.context_trimming_threshold)

    return messages


def create_phase_request(state: ModularState) -> List[StateRequest]:
    """Create phase request for prompter
    Note: this phase does not have operations, it just prepares the messages
    and updates the state. We kept this phase separate from the other phases
    to maintain the modularity of the original Modular agent.
    """
    messages = prepare_messages(state)
    state.messages = messages

    return [
        StateRequest(
            state=state,
            state_model="type_defs.states.ModularState",
            operations=[],
            next_phase="modular/phases/generator.py",
        )
    ]


if __name__ == "__main__":
    run_phase("prompter", create_phase_request, "type_defs.states.ModularState")
