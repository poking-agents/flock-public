import json

import pytest

import flock.modular.phases.actor as actor
from flock.type_defs.base import Node, Option
from flock.type_defs.operations import (
    BashRequest,
    GenerationOutput,
    GenerationResult,
    GetUsageOutput,
    GetUsageResult,
    LogWithAttributesRequest,
    MiddlemanModelOutput,
    MiddlemanSettings,
    RunUsage,
    SaveStateOutput,
    SaveStateResult,
    UsageCheckpoint,
)
from flock.type_defs.phases import StateRequest
from flock.type_defs.states import ModularSettings, ModularState


@pytest.mark.parametrize(
    ("thinking_text"),
    [None, "Hmm, let me think..."],
)
def test_create_phase_request(thinking_text: str | None):
    completion_content = "I have a an idea!"
    bash_command = "ls -la"
    thinking_block = (
        {
            "type": "thinking",
            "thinking": thinking_text,
            "signature": "signed by me",
        }
        if thinking_text
        else None
    )

    state = ModularState(
        id="123",
        nodes=[
            Node(
                source="actor_choice",
                options=[
                    Option(
                        content=completion_content,
                        function_call={
                            "name": "bash",
                            "arguments": json.dumps({"command": bash_command}),
                        },
                        thinking_blocks=[thinking_block] if thinking_block else [],
                    )
                ],
            )
        ],
        previous_results=[
            [
                GenerationResult(
                    type="generate",
                    result=GenerationOutput(
                        outputs=[
                            MiddlemanModelOutput(
                                completion=completion_content,
                                reasoning_completion=thinking_text or "",
                                function_call={
                                    "name": "bash",
                                    "arguments": '{"command": "ls -la"}',
                                },
                                extra_outputs={
                                    "content_blocks": [
                                        *([thinking_block] if thinking_block else []),
                                        {
                                            "type": "text",
                                            "text": completion_content,
                                        },
                                        {
                                            "type": "tool_use",
                                            "id": "toolu_01LxQXQwNMuZHgeUFEpEq8VB",
                                            "name": "bash",
                                            "input": {"command": "ls -la"},
                                        },
                                    ],
                                    "thinking": thinking_text or "",
                                    "thinking_was_redacted": False,
                                },
                            )
                        ],
                    ),
                    error=None,
                    metadata=None,
                ),
                SaveStateResult(
                    type="save_state",
                    result=SaveStateOutput(
                        status="success",
                        message="State snapshot",
                        snapshot_path="/dummy/path/to/state.json",
                    ),
                    error=None,
                    metadata=None,
                ),
                GetUsageResult(
                    type="get_usage",
                    result=GetUsageOutput(
                        checkpoint=UsageCheckpoint(
                            tokens=1716, actions=2, total_seconds=20, cost=0.2
                        ),
                        isPaused=False,
                        usage=RunUsage(
                            tokens=1716, actions=2, total_seconds=20, cost=0.2
                        ),
                        usageLimits=RunUsage(
                            tokens=300000, actions=3000, total_seconds=3000, cost=300.0
                        ),
                    ),
                    error=None,
                    metadata=None,
                ),
            ],
            [],
        ],
        settings=ModularSettings(
            generator=MiddlemanSettings(
                model="claude-3-7-sonnet-20250219",
            ),
        ),
    )

    state_requests = actor.create_phase_request(state)

    assert isinstance(state_requests, list)
    assert len(state_requests) == 1

    (state_request,) = state_requests
    assert isinstance(state_request, StateRequest)
    assert state_request.state is state
    assert state_request.state_model == "type_defs.states.ModularState"

    operations = state_request.operations
    assert len(operations) == 2

    assert isinstance(operations[0], LogWithAttributesRequest)
    assert operations[0].type == "log_with_attributes"
    content = operations[0].params.content
    if thinking_text:
        assert content.startswith("Thinking:\n")
        assert thinking_text in content
    else:
        assert content.startswith("Completion content:\n")
        assert "Thinking:" not in content

    assert "\nFunction called: bash with command:\n" in content
    assert bash_command in content

    assert isinstance(operations[1], BashRequest)
    assert operations[1].type == "bash"


def test_actor_set_timeout_with_integer_argument():
    """Test actor phase with set_timeout function call with integer argument"""

    state = ModularState(
        id="123",
        nodes=[
            Node(
                source="actor_choice",
                options=[
                    Option(
                        content="Some completion text",
                        function_call={
                            "name": "set_timeout",
                            "arguments": json.dumps({"timeout": 10}),
                        },
                    )
                ],
            )
        ],
        previous_results=[
            [
                GenerationResult(
                    type="generate",
                    result=GenerationOutput(
                        outputs=[
                            MiddlemanModelOutput(
                                completion="Some completion text",
                                reasoning_completion=None,
                                function_call={
                                    "name": "set_timeout",
                                    "arguments": '{"timeout": 10}',
                                },
                                usage=RunUsage(
                                    tokens=100, actions=1, total_seconds=10, cost=0.1
                                ),
                                usageLimits=RunUsage(
                                    tokens=300000,
                                    actions=3000,
                                    total_seconds=3000,
                                    cost=300.0,
                                ),
                                error=None,
                                metadata=None,
                            )
                        ],
                    ),
                    error=None,
                    metadata=None,
                )
            ],
            [],
        ],
        settings=ModularSettings(
            generator=MiddlemanSettings(
                model="claude-3-7-sonnet-20250219",
            ),
        ),
    )

    state_requests = actor.create_phase_request(state)

    assert isinstance(state_requests, list)
    assert len(state_requests) == 1

    (state_request,) = state_requests
    assert isinstance(state_request, StateRequest)
    assert state_request.state is state
    assert state_request.state_model == "type_defs.states.ModularState"

    operations = state_request.operations
    assert len(operations) == 1

    nodes = state_request.state.nodes
    assert len(nodes) == 2

    assert isinstance(operations[0], LogWithAttributesRequest)
    assert operations[0].type == "log_with_attributes"
    content = operations[0].params.content
    assert "Function called: set_timeout with timeout:\n10" in content
