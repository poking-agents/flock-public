"""Evaluate subagent results using tournament-style comparisons"""

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.append(str(Path(__file__).parent.parent.parent))
from type_defs import Message
from type_defs.operations import GenerationParams, GenerationRequest, OperationMetadata
from type_defs.phases import StateRequest
from type_defs.states import TournamentMatch, triframeState
from utils.phase_utils import run_phase
from utils.state import load_state


def get_tournament_function() -> Dict[str, Any]:
    """Get the tournament evaluation function definition"""
    return {
        "name": "select_winner",
        "description": "Select the winner of a head-to-head comparison between subagents",
        "parameters": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Detailed explanation of why this agent's approach and results were better",
                },
                "winner_id": {
                    "type": "string",
                    "description": "ID of the winning agent",
                },
            },
            "required": ["winner_id", "reasoning"],
        },
    }


def format_tournament_prompt(state: triframeState, agent1: dict, agent2: dict) -> str:
    """Format prompt for evaluating a pair of candidates"""
    agent1_state = load_state(agent1["id"])
    agent2_state = load_state(agent2["id"])

    def format_recent_activity(nodes: List[Dict], limit: int = 10) -> str:
        if not nodes:
            return "No activity recorded"
        recent = nodes[-limit:]
        return "\n".join(
            f"""<{node['source']}>{node['options'][0]['content']}
    {node['options'][0].get('function_call', '')}</{node['source']}>"""
            for node in recent
        )

    return f"""Compare these two agents working on this task:
<task_description>
{state.task_string}
</task_description>

Agent ids: {agent1['id']} and {agent2['id']}. Use the complete id when selecting a winner.

<{agent1['id']}>
Task: {agent1.get('task', 'No task specified')}
Approach: {agent1['approach']}

Recent Activity (last 10 nodes):
{format_recent_activity(agent1_state.get('nodes', []))}

Result: {agent1.get('result', 'No result yet')}
</{agent1['id']}>

<{agent2['id']}>
Task: {agent2.get('task', 'No task specified')}
Approach: {agent2['approach']}

Recent Activity (last 10 nodes):
{format_recent_activity(agent2_state.get('nodes', []))}

Result: {agent2.get('result', 'No result yet')}
</{agent2['id']}>

Compare these agents' approaches and results.
Which one showed more promise? Consider:
1. Progress made toward the goal
2. Quality and sophistication of approach
3. Milestones achieved
4. Effectiveness of execution
5. Quality of final result

Use the select_winner function to indicate your choice (an agent id)."""


def pair_agents(agents: List[dict]) -> List[List[dict]]:
    """Create tournament pairs from agent list"""
    pairs = []
    for i in range(0, len(agents), 2):
        if i + 1 < len(agents):
            pairs.append([agents[i], agents[i + 1]])
        else:
            pairs.append([agents[i]])
    return pairs


def create_phase_request(state: triframeState) -> List[StateRequest]:
    """Create evaluation phase request using tournament format"""
    tournament = state.get_current_tournament()
    if not tournament or tournament.status != "in_progress":
        raise ValueError("No in-progress tournament found")
    if tournament.rounds:
        current_round = tournament.rounds[-1]
        if not all(match.winner_id is not None for match in current_round.matches):
            raise ValueError("Tournament has not been processed")
            return [
                StateRequest(
                    state=state,
                    state_model="type_defs.states.triframeState",
                    operations=[],
                    next_phase="triframe/phases/subagents_process.py",
                )
            ]
    active_agents = tournament.active_agents
    # if we get here with 1, it's a bye, and can be handled here
    # if len(active_agents) <= 1:
    #     return [
    #         StateRequest(
    #             state=state,
    #             state_model="type_defs.states.triframeState",
    #             operations=[],
    #             next_phase="triframe/phases/subagents_process.py",
    #         )
    #     ]
    pairs = pair_agents(active_agents)
    operations = []
    matches = []
    for pair_index, pair in enumerate(pairs):
        if len(pair) == 1:
            match = TournamentMatch(
                agents=[pair[0]],
                winner_id=pair[0],
                reasoning="Advanced via bye",
                task=tournament.task,
            )
            matches.append(match)
        else:
            match = TournamentMatch(agents=pair, task=tournament.task)
            matches.append(match)
            messages = [
                Message(
                    role="system",
                    content=format_tournament_prompt(
                        state,
                        next(a for a in state.active_subagents if a["id"] == pair[0]),
                        next(a for a in state.active_subagents if a["id"] == pair[1]),
                    ),
                ).dict()
            ]
            operations.append(
                GenerationRequest(
                    type="generate",
                    params=GenerationParams(
                        messages=messages,
                        settings=state.settings.actors[0],
                        functions=[get_tournament_function()],
                        function_call={"name": "select_winner"},
                    ),
                    metadata=OperationMetadata(
                        purpose="tournament_match",
                        tournament_id=tournament.id,
                        round_number=len(tournament.rounds),
                        match_index=pair_index,
                        agent_ids=pair,
                    ),
                )
            )
    if matches:
        state.add_tournament_round(tournament, matches)
    return [
        StateRequest(
            state=state,
            state_model="type_defs.states.triframeState",
            operations=operations,
            next_phase="triframe/phases/subagents_process.py",
        )
    ]


if __name__ == "__main__":
    run_phase(
        "subagents_evaluate", create_phase_request, "type_defs.states.triframeState"
    )
