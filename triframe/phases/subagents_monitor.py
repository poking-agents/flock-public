"""Monitor subagent execution progress"""

import json
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directories to path for both local and hooks environments
current_dir = Path(__file__).parent
sys.path.extend(
    [
        str(current_dir.parent.parent),  # For local environment
        str(Path("/home/agent/.agent_code")),  # For hooks environment
    ]
)

try:
    from triframe.logging import log_system, log_warning
    from type_defs import Node, Option
    from type_defs.phases import StateRequest
    from type_defs.states import triframeState
    from utils.phase_utils import run_phase
    from utils.state import load_state
except ImportError:
    # Try alternate import path for hooks environment
    sys.path.append("/home/agent/.agent_code")
    from triframe.logging import log_system, log_warning
    from type_defs import Node, Option
    from type_defs.phases import StateRequest
    from type_defs.states import triframeState
    from utils.phase_utils import run_phase
    from utils.state import load_state


def load_agent_state(agent_id: str) -> Optional[dict]:
    """Safely load an agent's state file"""
    try:
        return load_state(agent_id)
    except FileNotFoundError:
        log_warning(f"Could not find state file for agent {agent_id}")
        return None
    except json.JSONDecodeError:
        log_warning(f"Could not parse state file for agent {agent_id}")
        return None
    except Exception as e:
        log_warning(f"Error reading state for agent {agent_id}: {str(e)}")
        return None


def check_agent_statuses(state: triframeState) -> bool:
    """Check if all agents have completed or failed"""
    current_round = state.active_subagents
    if not current_round:
        return False

    # Update status from state files
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


def create_phase_request(state: triframeState) -> List[StateRequest]:
    """Create monitor phase request"""
    try:
        if not state.active_subagents:
            state.nodes.append(
                Node(
                    source="tool_output",
                    options=[
                        Option(
                            content="No active subagents to monitor",
                            name="launch_subagents",
                            metadata={"error": "No active subagents"},
                        )
                    ],
                )
            )
            return [
                StateRequest(
                    state=state,
                    state_model="type_defs.states.triframeState",
                    operations=[
                        log_warning("No active subagents to monitor"),
                    ],
                    next_phase="triframe/phases/advisor.py",
                )
            ]

        if check_agent_statuses(state):
            return [
                StateRequest(
                    state=state,
                    state_model="type_defs.states.triframeState",
                    operations=[
                        log_system(
                            "All agents have completed. Starting tournament evaluation..."
                        ),
                    ],
                    next_phase="triframe/phases/subagents_evaluate.py",
                )
            ]

        # Continue monitoring
        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=[],
                next_phase="triframe/phases/subagents_monitor.py",
                delay=10,  # Check every 10 seconds
            )
        ]
    except Exception as e:
        # If anything goes wrong, log it and return to advisor with a tool output node
        error_msg = f"Error in monitor phase: {str(e)}"
        state.nodes.append(
            Node(
                source="tool_output",
                options=[
                    Option(
                        content=error_msg,
                        name="launch_subagents",
                        metadata={"error": str(e)},
                    )
                ],
            )
        )
        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=[
                    log_warning(
                        f"Monitor phase failed, returning to advisor: {str(e)}"
                    ),
                ],
                next_phase="triframe/phases/advisor.py",
            )
        ]


if __name__ == "__main__":
    run_phase(
        "subagents_monitor", create_phase_request, "type_defs.states.triframeState"
    )