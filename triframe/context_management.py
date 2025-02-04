import sys
from pathlib import Path
from typing import List, Tuple

sys.path.append(str(Path(__file__).parent.parent))
from type_defs import Message, Node, triframeState


def trim_content(content: str, max_length: int = 10000) -> str:
    if len(content) <= max_length:
        return content
    portion_size = max_length // 2
    return f"""{content[:portion_size]}
... [trimmed {len(content) - max_length} characters] ...
{content[-portion_size:]}"""


def limit_name_and_max(state: triframeState) -> Tuple[str, int]:
    limit_type = state.settings.limit_type
    if limit_type == "token":
        limit_max = state.token_limit
    elif limit_type == "action":
        limit_max = state.actions_limit
    elif limit_type == "time":
        limit_max = int(state.time_limit)
    else:
        raise ValueError(f"Invalid limit type: {limit_type}")
    limit_name = "second" if limit_type == "time" else limit_type
    return limit_name, limit_max


def limit_name_usage_max(state: triframeState, node: Node) -> Tuple[str, int, int]:
    """Get the limit name, usage, and max for the given node"""
    name, max = limit_name_and_max(state)
    limit_type = state.settings.limit_type
    if limit_type == "token":
        limit_usage = node.token_usage
    elif limit_type == "action":
        limit_usage = node.actions_usage
    elif limit_type == "time":
        limit_usage = int(node.time_usage)
    else:
        raise ValueError(f"Invalid limit type: {limit_type}")
    return name, limit_usage, max


def tool_output_with_usage(state: triframeState, node: Node) -> str:
    option = node.options[0]
    limit_name, limit_usage, limit_max = limit_name_usage_max(state, node)
    if limit_usage is None or limit_max is None:
        raise ValueError("Usage or limit not set")
    usage_notice = f"{limit_usage} of {limit_max} {limit_name}s used"

    # add warning when close to limit
    if limit_usage > limit_max * 0.95 or limit_usage > limit_max - 50_000:
        usage_notice += (
            "\nWarning: You are close to the limit. Submit your work in the next round."
        )
    elif limit_usage > limit_max * 0.8:
        usage_notice += (
            "\nWarning: You are close to the limit. Prepare to submit your work soon."
        )

    return f"""{option.content}\n{usage_notice}"""


def merge_consecutive_user_messages(messages: List[Message]) -> List[Message]:
    merged_messages: List[Message] = []
    for message in messages:
        if (
            message.role == "user"
            and merged_messages
            and merged_messages[-1].role == "user"
        ):
            merged_messages[-1].content += f"\n{message.content}"
        else:
            merged_messages.append(message)
    return merged_messages
