from pyhooks.types import MiddlemanSettings

from flock.modular.phases.prompter import prepare_messages
from flock.type_defs.base import Node, Option
from flock.type_defs.states import ModularSettings, ModularState


def test_prepare_messages_preserves_reasoning_details():
    reasoning_details = [
        {"type": "reasoning.text", "text": "step-by-step", "id": "reason-1"}
    ]
    content_blocks = [
        {"type": "thinking", "text": "consider tools", "signature": "sig-1"},
        {
            "type": "tool_use",
            "id": "call-1",
            "name": "bash",
            "input": {"command": "ls"},
        },
    ]
    option = Option(
        content="fallback completion",
        function_call={"name": "bash", "arguments": '{"command": "ls"}'},
        reasoning_details=reasoning_details,
        content_blocks=content_blocks,
    )
    state = ModularState(
        id="state-1",
        nodes=[Node(source="actor_choice", options=[option])],
        messages=[],
        settings=ModularSettings(generator=MiddlemanSettings(model="test-model")),
    )

    messages = prepare_messages(state)
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]

    assert assistant_messages, "Expected at least one assistant message"
    assistant_message = assistant_messages[0]
    assert assistant_message.content == content_blocks
    assert assistant_message.reasoning_details == reasoning_details
    # When content_blocks are present, function_call should not be set separately
    assert assistant_message.function_call is None

    # Ensure no duplicate reasoning-only messages were appended
    assert all(
        msg.reasoning_details is None or msg is assistant_message
        for msg in assistant_messages
    )

