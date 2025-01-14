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

def tool_output_with_usage(state: triframeState, node: Node) -> str:
    if node.time_usage is None or node.token_usage is None:
        raise ValueError("Time or token usage not set")
    
    if state.time_limit is None or state.token_limit is None:
        raise ValueError("Time or token limit not set")

    time_usage_notice = f"Time usage (s): {node.time_usage} of {state.time_limit} used"
    token_usage_notice = f"Token usage: {node.token_usage} of {state.token_limit} used"
    option = node.options[0]
    return f"""{option.content}\n{time_usage_notice}\n{token_usage_notice}"""


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
