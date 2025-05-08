"""Generator phase for modular workflow"""

from typing import List

from flock.modular.templates import BASIC_SYSTEM_PROMPT
from flock.type_defs.base import Message
from flock.type_defs.operations import (
    GenerationParams,
    GenerationRequest,
)
from flock.type_defs.phases import StateRequest
from flock.type_defs.states import ModularState
from flock.utils.functions import get_standard_function_definitions
from flock.utils.phase_utils import add_usage_request, run_phase


def create_phase_request(state: ModularState) -> List[StateRequest]:
    """Create phase request for generator"""
    initial_messages = [
        Message(role="user", content=BASIC_SYSTEM_PROMPT),
        Message(
            role="user", content="You are assigned this task: " + state.task_string
        ),
    ]
    messages = [*initial_messages, *state.messages]
    params = GenerationParams(
        messages=[msg.dict() for msg in messages],
        settings=state.settings.generator,
        functions=get_standard_function_definitions(state),
    )

    operations = [GenerationRequest(type="generate", params=params)]
    operations = add_usage_request(operations)

    return [
        StateRequest(
            state=state,
            state_model="type_defs.states.ModularState",
            operations=operations,
            next_phase="modular/phases/discriminator.py",
        )
    ]


if __name__ == "__main__":
    run_phase("generator", create_phase_request, "type_defs.states.ModularState")
