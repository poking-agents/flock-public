"""Generator phase for modular workflow"""

import sys
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).parent.parent.parent))

from modular.templates import BASIC_SYSTEM_PROMPT
from type_defs.base import Message
from type_defs.operations import (
    GenerationParams,
    GenerationRequest,
)
from type_defs.phases import StateRequest
from type_defs.states import ModularState
from utils.functions import get_standard_function_definitions
from utils.phase_utils import add_usage_request, run_phase


def create_phase_request(state: ModularState) -> List[StateRequest]:
    """Create phase request for generator"""
    initial_messages = [
        Message(role="system", content=BASIC_SYSTEM_PROMPT),
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
