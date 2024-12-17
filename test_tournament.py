"""Test script for tournament evaluation process"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import aiohttp
from pydantic import BaseModel

from type_defs import Node, Option
from type_defs.operations import MiddlemanSettings
from type_defs.states import triframeState, triframeSettings
from utils.state import save_state
from handlers.utility import icpc_instructions


def create_main_state(state_id: str) -> triframeState:
    """Create main agent state with ICPC task and 3 subagents"""
    settings = triframeSettings(
        actors=[MiddlemanSettings(model="gpt-4o-mini", temp=0.7, n=1)],
        advisors=[MiddlemanSettings(model="gpt-4o-mini", temp=0.0, n=1)],
        raters=[MiddlemanSettings(model="gpt-4o-mini", temp=0.2, n=1)],
        limit_type="token",
        intermediate_scoring=False,
        require_function_call=True,
        enable_advising=True,
        enable_subagents=True,
    )

    state = triframeState(
        id=state_id,
        task_string=icpc_instructions,
        settings=settings,
        previous_results=[],
        nodes=[],
        token_limit=300000,
        token_usage=0,
        actions_limit=1000,
        actions_usage=0,
        time_limit=604800.0,
        time_usage=0.0,
        timeout=60,
        context_trimming_threshold=80000,
        output_limit=10000,
    )

    # Add subagents with different approaches
    approaches = [
        {
            "id": f"agent_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "task": "Implement a solution to the Devil of Gravity problem",
            "approach": approach,
            "include_task_description": True,
            "status": "concluded",
        }
        for i, approach in enumerate(
            [
                "Use a stack-based approach to handle falling segments",
                "Implement a grid-based solution with gravity simulation",
                "Use string manipulation with segment tracking",
            ]
        )
    ]

    for agent in approaches:
        state.add_subagent(
            agent_id=agent["id"],
            task=agent["task"],
            approach=agent["approach"],
            include_task_description=agent["include_task_description"],
        )

    return state


def create_subagent_state(
    agent_config: Dict[str, Any], parent_id: str
) -> triframeState:
    """Create a completed subagent state with execution history"""
    state = triframeState(
        id=agent_config["id"],
        task_string=agent_config["task"],
        settings=triframeSettings(
            actors=[MiddlemanSettings(model="gpt-4o-mini", temp=0.7, n=1)],
            advisors=[MiddlemanSettings(model="gpt-4o-mini", temp=0.0, n=1)],
            raters=[MiddlemanSettings(model="gpt-4o-mini", temp=0.2, n=1)],
        ),  # Use default settings with required model fields
        previous_results=[],
        nodes=[
            # Add some realistic execution history
            Node(
                source="actor_choice",
                options=[
                    Option(
                        content="Let me implement a solution using "
                        + agent_config["approach"],
                        function_call={
                            "name": "run_bash",
                            "arguments": json.dumps(
                                {"command": "echo 'Starting implementation'"}
                            ),
                        },
                    )
                ],
            ),
            Node(
                source="tool_output",
                options=[Option(content="Starting implementation", name="run_bash")],
            ),
            # Add conclude node to mark completion
            Node(
                source="actor_choice",
                options=[
                    Option(
                        content="Implementation complete",
                        function_call={
                            "name": "conclude",
                            "arguments": json.dumps(
                                {
                                    "result": f"Completed implementation using {agent_config['approach']}"
                                }
                            ),
                        },
                    )
                ],
            ),
        ],
        token_limit=150000,  # Half of parent's limit
        token_usage=5000,
        actions_limit=500,
        actions_usage=10,
        time_limit=302400.0,
        time_usage=100.0,
        timeout=60,
        context_trimming_threshold=80000,
        output_limit=10000,
        subagent_config={
            "approach": agent_config["approach"],
            "parent_id": parent_id,
            "created_at": datetime.now().isoformat(),
        },
        status="concluded",  # Mark as concluded
    )
    return state


async def run_monitor_phase(state_id: str) -> Dict[str, Any]:
    """Run the monitor phase via workflow request"""
    async with aiohttp.ClientSession() as session:
        payload = {
            "state_id": state_id,
            "current_phase": "test_tournament",
            "operations": [],
            "next_phase": "triframe/phases/subagents_monitor.py",
        }

        async with session.post(
            "http://localhost:8080/run_workflow", json=payload
        ) as response:
            if response.status != 200:
                raise Exception(f"Workflow request failed: {await response.text()}")
            return await response.json()


async def run_tournament_test():
    """Run the tournament evaluation process"""
    # Create main state
    main_state_id = f"tournament_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    main_state = create_main_state(main_state_id)

    # Create and save subagent states
    for agent in main_state.active_subagents:
        subagent_state = create_subagent_state(agent, main_state_id)
        save_state(agent["id"], subagent_state)

    # Save main state
    save_state(main_state_id, main_state)

    print(f"\nCreated test states:")
    print(f"Main state ID: {main_state_id}")
    print("Subagent IDs:")
    for agent in main_state.active_subagents:
        print(f"  - {agent['id']}: {agent['approach']}")

    print("\nRunning monitor phase...")
    result = await run_monitor_phase(main_state_id)
    print("\nMonitor phase result:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(run_tournament_test())
