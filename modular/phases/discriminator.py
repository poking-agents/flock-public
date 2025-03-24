"""Discriminator phase for modular workflow"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).parent.parent.parent))

from type_defs.base import Message, Option
from type_defs.phases import StateRequest
from type_defs.states import ModularState, Node
from utils.logging import log_warning
from utils.phase_utils import get_thinking_block, results_of_type, run_phase


def parse_ratings(option: Message) -> Optional[Dict[int, List[float]]]:
    """Parse ratings from a ratings node"""
    ratings_by_option = {}
    try:
        function_call = option.function_call
        if not function_call:
            return {}
        ratings_array = json.loads(function_call["arguments"])["ratings"]
        for rating in ratings_array:
            option_idx = rating["option_index"]
            if option_idx not in ratings_by_option:
                ratings_by_option[option_idx] = []
            ratings_by_option[option_idx].append(rating["rating"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    return ratings_by_option


def create_phase_request(state: ModularState) -> List[StateRequest]:
    """Create phase request for discriminator"""
    # Get generation results
    generation_results = results_of_type(state.previous_results[-1], "generate")
    if not generation_results:
        raise ValueError("No generation results found")

    # Process all outputs into options
    options = []
    for result in generation_results:
        if not result.result.outputs:
            continue
        for output in result.result.outputs:
            if output.completion or output.function_call:
                thinking_block = get_thinking_block(output)
                options.append(
                    Option(
                        content=output.completion,
                        function_call=output.function_call,
                        thinking_block=thinking_block,
                    )
                )

    # Handle no valid options
    if not options:
        warning = log_warning("No valid options generated, retrying generation")
        state.update_usage()
        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.ModularState",
                operations=[warning],
                next_phase="modular/phases/generator.py",
            )
        ]

    # Just take the first option (basic discriminator)
    state.nodes.append(Node(source="actor_choice", options=[options[0]]))
    state.update_usage()
    return [
        StateRequest(
            state=state,
            state_model="type_defs.states.ModularState",
            operations=[],
            next_phase="modular/phases/actor.py",
        )
    ]


if __name__ == "__main__":
    run_phase("discriminator", create_phase_request, "type_defs.states.ModularState")
