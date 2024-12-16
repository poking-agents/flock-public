"""Process tournament evaluation results"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any

sys.path.append(str(Path(__file__).parent.parent.parent))

from type_defs import Node, Option
from type_defs.phases import StateRequest
from type_defs.states import triframeState
from utils.phase_utils import get_last_function_call, run_phase


def process_tournament_results(state: triframeState) -> List[Dict[str, Any]]:
    """Process tournament results and get winners"""
    # First check for single-agent tournament result
    for node in reversed(state.nodes):
        if node.source == "subagent_tournament_results" and node.options:
            metadata = node.options[0].metadata
            if "winners" in metadata:
                return metadata["winners"]

    # Otherwise process normal tournament results
    winners = []
    for node in state.nodes:
        if (
            node.source == "subagent_tournament"
            and node.options
            and "advanced_agent" in node.options[0].metadata
        ):
            winners.append(node.options[0].metadata["advanced_agent"])

    # Only process generation results if we have them
    if state.previous_results and state.previous_results[-1]:
        for result in state.previous_results[-1]:
            if result.type == "generate":
                function_call = get_last_function_call([result])
                if function_call and function_call["name"] == "select_winner":
                    try:
                        args = json.loads(function_call["arguments"])
                        winner_id = args["winner_id"]
                        reasoning = args["reasoning"]
                        winner = next(
                            a for a in state.active_subagents if a["id"] == winner_id
                        )
                        winner["reasoning"] = reasoning
                        winners.append(winner)
                    except Exception as e:
                        print(f"Error processing tournament result: {str(e)}")
                        continue
    return winners


def create_phase_request(state: triframeState) -> List[StateRequest]:
    """Process evaluation results and decide next step"""
    winners = process_tournament_results(state)

    if len(winners) == 1:
        winner = winners[0]
        # Add tournament results to state
        state.nodes.append(
            Node(
                source="tool_output",
                options=[
                    Option(
                        content=f"""Tournament complete. Winner: {winner['id']}
Task: {winner['task']}
Approach: {winner['approach']}
Reasoning: {winner.get('reasoning', 'No reasoning provided')}""",
                        name="launch_subagents",
                        metadata={"winner": winner},
                    )
                ],
            )
        )
        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=[],
                next_phase="triframe/phases/advisor.py",
            )
        ]
    else:
        # Continue tournament with remaining agents
        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=[],
                next_phase="triframe/phases/subagents_evaluate.py",
            )
        ]


if __name__ == "__main__":
    run_phase(
        "subagents_process", create_phase_request, "type_defs.states.triframeState"
    )