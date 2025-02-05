from triframe.phases.advisor_ratings import create_phase_request
from type_defs.states import triframeState, triframeSettings
from type_defs.operations import (
    GenerationResult,
    GenerationOutput,
    MiddlemanModelOutput,
    MiddlemanSettings,
)


def test_multiple_think_tags_warning():
    state = triframeState(
        task_string="test task",
        nodes=[],
        settings=triframeSettings(
            enable_tool_use=True,
            enable_xml=False,
            raters=[MiddlemanSettings(model="gpt-4o-mini")],
            actors=[MiddlemanSettings(model="gpt-4o-mini")],
            advisors=[MiddlemanSettings(model="gpt-4o-mini")],
            require_function_call=False,
        ),
        previous_results=[
            [
                GenerationResult(
                    type="generate",
                    result=GenerationOutput(
                        outputs=[
                            MiddlemanModelOutput(
                                completion="<think>first thought</think><think>second thought</think>",
                                function_call=None,
                            )
                        ]
                    ),
                )
            ]
        ],
    )

    # Call the function
    state_requests = create_phase_request(state)
    assert len(state_requests) == 1
    state_request = state_requests[0]

    assert len(state_request.operations) == 2

    skip_warning = state_request.operations[0]

    # Verify the warning message
    expected_message = "Skipping output with multiple </think> tags: <think>first thought</think><think>second thought</think>..."
    assert skip_warning.params.content == expected_message

    # Verify we're returning to actor phase
    assert state_request.next_phase == "triframe/phases/actor.py"
