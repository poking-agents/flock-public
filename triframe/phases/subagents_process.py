"""Process tournament evaluation results"""

import json
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.append(str(Path(__file__).parent.parent.parent))
from triframe.logging import log_subagent_output, log_system, log_warning
from triframe.phases.subagents_monitor import load_agent_state
from type_defs import Node, Option
from type_defs.operations import OperationRequest
from type_defs.phases import StateRequest
from type_defs.states import triframeState
from utils.phase_utils import get_last_function_call, run_phase


def check_agent_statuses(state: triframeState) -> bool:
    """Check if all agents have completed or failed"""
    current_round = state.active_subagents
    if not current_round:
        return False
    for agent in current_round:
        agent_state = load_agent_state(agent["id"])
        if agent_state is None:
            agent["status"] = "failed"
            continue
        try:
            agent["status"] = agent_state.get("status", "running")
        except Exception as e:
            agent["status"] = "failed"
            log_warning(f"Error getting status for agent {agent['id']}: {str(e)}")
    return all(agent["status"] in ["concluded", "failed"] for agent in current_round)


def process_tournament_results(
    state: triframeState,
) -> Tuple[List[OperationRequest], triframeState]:
    """Process tournament results and return updated state"""
    operations = []
    original_state = state
    tournament = state.get_current_tournament()
    if (
        not tournament
        or not state.previous_results
        or not state.previous_results[-1]
        or not tournament.rounds
    ):
        operations.append(log_system("No tournament results to process"))
        return operations, state
    current_round = tournament.rounds[-1]
    new_active_agents = tournament.active_agents.copy()
    for result in state.previous_results[-1]:
        if result.type == "generate":
            operations.append(
                log_system(f"Processing generation result {result.result.model_dump()}")
            )
            if not (result.metadata and result.metadata.purpose == "tournament_match"):
                continue
            if (
                result.metadata.tournament_id != tournament.id
                or result.metadata.round_number != len(tournament.rounds) - 1
                or result.metadata.match_index >= len(current_round.matches)
            ):
                continue
            match = current_round.matches[result.metadata.match_index]
            if match.winner_id is not None:
                continue
            function_call = get_last_function_call([result])
            if function_call and function_call["name"] == "select_winner":
                try:
                    args = json.loads(function_call["arguments"])
                    winner_id = args["winner_id"]
                    reasoning = args["reasoning"]
                    if winner_id not in result.metadata.agent_ids:
                        operations.append(
                            log_warning(
                                f"Winner {winner_id} not in match agents {result.metadata.agent_ids}"
                            )
                        )
                        continue
                    if set(match.agents) != set(result.metadata.agent_ids):
                        operations.append(
                            log_warning(
                                f"Warning: Match agents mismatch. Expected {match.agents}, got {result.metadata.agent_ids}"
                            )
                        )
                        continue
                    match.winner_id = winner_id
                    match.reasoning = reasoning
                    new_active_agents = [
                        a
                        for a in new_active_agents
                        if a == winner_id or a not in match.agents
                    ]
                except Exception as e:
                    operations.append(
                        log_warning(f"Error processing match result: {str(e)}")
                    )
                    continue
    tournament.active_agents = new_active_agents
    all_matches_complete = all(
        match.winner_id is not None for match in current_round.matches
    )
    if all_matches_complete and len(tournament.active_agents) == 1:
        winner_id = tournament.active_agents[0]
        state.complete_tournament(tournament, winner_id)
    original_dict = original_state.dict()
    new_dict = state.dict()
    diff = {}
    try:
        for key in original_dict:
            if original_dict[key] != new_dict[key]:
                diff[key] = new_dict[key]
    except KeyError:
        pass
    operations.append(log_system(f"State diff: {diff}"))
    return operations, state


def create_phase_request(state: triframeState) -> List[StateRequest]:
    """Process evaluation results and decide next step"""
    operations, state = process_tournament_results(state)
    tournament = state.get_current_tournament()
    if tournament and tournament.status == "completed":
        winner = next(
            a for a in state.active_subagents if a["id"] == tournament.winner_id
        )
        summary_parts = []
        for round_num, round in enumerate(tournament.rounds, 1):
            summary_parts.append(f"\nRound {round_num}:")
            for match in round.matches:
                if len(match.agents) > 1:
                    summary_parts.append(
                        f"""Match: {' vs '.join(match.agents)}
Winner: {match.winner_id}
Reasoning: {match.reasoning}"""
                    )
        tournament_summary = "\n".join(summary_parts)
        state.active_subagents = [
            agent for agent in state.active_subagents if agent["id"] == winner["id"]
        ]
        subagent_output = Node(
            source="tool_output",
            options=[
                Option(
                    content=f"""Tournament complete. Winner: {winner['id']}
Task: {winner['task']}
Approach: {winner['approach']}

Tournament Results:
{tournament_summary}""",
                    metadata={"winner": winner},
                )
            ],
        )
        state.nodes.append(subagent_output)
        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=[log_subagent_output(subagent_output.options[0].content)],
                next_phase="triframe/phases/advisor.py",
            )
        ]
    else:
        if tournament and tournament.status == "in_progress":
            return [
                StateRequest(
                    state=state,
                    state_model="type_defs.states.triframeState",
                    operations=operations,
                    next_phase="triframe/phases/subagents_evaluate.py",
                )
            ]
        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=operations,
                next_phase="triframe/phases/advisor.py",
            )
        ]


if __name__ == "__main__":
    run_phase(
        "subagents_process", create_phase_request, "type_defs.states.triframeState"
    )
