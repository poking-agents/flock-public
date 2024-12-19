import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent))

from utils.phase_utils import get_model_class, run_main
from type_defs.phases import StateRequest
from type_defs.states import BaseState


def load_state(state_path: str) -> Dict[str, Any]:
    """Load state from the specified JSON file"""
    with open(state_path, "r") as f:
        return json.load(f)


async def test_phase(state_path: str, phase_path: str):
    """Test a phase against a specified state"""
    # Load the state
    state_dict = load_state(state_path)

    # Determine the state model
    state_model = state_dict.get("state_model", "type_defs.states.DuetState")

    # Get the state model class
    state_model_class = get_model_class(state_model)

    # Create the state object
    state = state_model_class(**state_dict)

    # Import the phase module
    phase_module = __import__(
        phase_path.replace("/", ".").rstrip(".py"), fromlist=["create_phase_request"]
    )
    create_phase_request = getattr(phase_module, "create_phase_request")

    # Run the phase
    state_requests = create_phase_request(state)

    # Print the results
    print(f"Phase {phase_path} output:")
    for i, request in enumerate(state_requests):
        print(f"\nRequest {i + 1}:")
        print(f"  Next phase: {request.next_phase}")
        print(f"  Operations:")
        for op in request.operations:
            print(f"    - Type: {op.type}")
            print(f"      Params: {op.params}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python test_phase.py <state_path> <phase_path>")
        sys.exit(1)

    state_path = sys.argv[1]
    phase_path = sys.argv[2]

    asyncio.run(test_phase(state_path, phase_path))
