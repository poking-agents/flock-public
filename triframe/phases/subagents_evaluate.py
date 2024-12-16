"""Evaluate subagent results using tournament-style comparisons"""

import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.append(str(Path(__file__).parent.parent.parent))

from type_defs import Message, Node, Option
from type_defs.operations import GenerationParams, GenerationRequest
from type_defs.phases import StateRequest
from type_defs.states import triframeState
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
    # Load detailed state for each agent
    agent1_state = load_state(agent1["id"])
    agent2_state = load_state(agent2["id"])

    # Format recent activity for each agent
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
    current_round = state.active_subagents
    agents = [a for a in current_round if a["status"] != "bye"]

    # If there's only one agent, skip tournament and mark it as winner
    if len(agents) == 1:
        winner = agents[0]
        state.nodes.append(
            Node(
                source="subagent_tournament_results",
                options=[
                    Option(
                        content=f"Single agent tournament - {winner['id']} is winner by default",
                        metadata={"winners": [winner]},
                    )
                ],
            )
        )
        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=[],
                next_phase="triframe/phases/subagents_process.py",
            )
        ]

    operations = []
    pairs = pair_agents(agents)
    for pair in pairs:
        if len(pair) == 1:
            state.nodes.append(
                Node(
                    source="subagent_tournament",
                    options=[
                        Option(
                            content=f"Agent {pair[0]['id']} advances",
                            metadata={"advanced_agent": pair[0]},
                        )
                    ],
                )
            )
            continue

        messages = [
            Message(
                role="system", content=format_tournament_prompt(state, pair[0], pair[1])
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
            )
        )

        state.nodes.append(
            Node(
                source="subagent_tournament",
                options=[
                    Option(
                        content="Tournament comparison",
                        metadata={
                            "pair": [a["id"] for a in pair],
                            "round": len(state.nodes),
                        },
                    )
                ],
            )
        )

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