import pytest

from type_defs.base import Option, RedactedThinkingBlock, VisibleThinkingBlock


@pytest.mark.parametrize(
    "thinking_blocks",
    [
        pytest.param(
            [
                {
                    "type": "thinking",
                    "thinking": "thinking block 1",
                    "signature": "thinking_block_1",
                },
            ],
            id="single-thinking-block",
        ),
        pytest.param(
            [
                {
                    "type": "redacted_thinking",
                    "data": "redacted thinking block",
                },
            ],
            id="single-redacted-thinking-block",
        ),
        pytest.param(
            [
                {
                    "type": "thinking",
                    "thinking": "thinking block 1",
                    "signature": "thinking_block_1",
                },
                {
                    "type": "redacted_thinking",
                    "data": "redacted thinking block",
                },
            ],
            id="multiple-thinking-blocks",
        ),
        pytest.param([], id="no-thinking-blocks"),
    ],
)
def test_option_with_thinking_blocks(thinking_blocks):
    """Test that Option accepts various formats of thinking blocks."""
    # Create option with the specified thinking blocks
    option = Option(content="Sample option text", thinking_blocks=thinking_blocks)
    for block, expected in zip(option.thinking_blocks, thinking_blocks):
        assert block.type == expected["type"]
        if block.type == "thinking":
            assert isinstance(block, VisibleThinkingBlock)
            assert block.thinking == expected["thinking"]
            assert block.signature == expected["signature"]
        elif block.type == "redacted_thinking":
            assert isinstance(block, RedactedThinkingBlock)
            assert block.data == expected["data"]
