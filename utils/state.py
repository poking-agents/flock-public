"""State management utilities"""

import json
from typing import Any, Dict, Optional, Type
import copy

from pydantic import BaseModel

from config import STATES_DIR

STATE_CHAR_LIMIT = 100_000


def load_state(
    state_id: str, schema: Optional[Type[BaseModel]] = None
) -> Dict[str, Any]:
    state_file = STATES_DIR / f"{state_id}.json"
    try:
        with open(state_file, "r") as f:
            state = json.load(f)
        if schema:
            validated = schema(**state)
            return validated.dict()
        return state
    except FileNotFoundError:
        raise FileNotFoundError(f"State file {state_file} not found")


def save_state(
    state_id: str, state: Dict[str, Any], schema: Optional[Type[BaseModel]] = None
) -> None:
    if schema:
        if isinstance(state, schema):
            state = state.model_dump()
        else:
            validated = schema(**state)
            state = validated.model_dump()
    elif isinstance(state, BaseModel):
        state = state.model_dump()
    state = trim_state(state, STATE_CHAR_LIMIT)
    STATES_DIR.mkdir(exist_ok=True)
    state_file = STATES_DIR / f"{state_id}.json"
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def trim_state(state: Dict[str, Any], char_limit: int) -> Dict[str, Any]:
    # Create a deep copy of the state to avoid modifying the original
    trimmed_state = copy.deepcopy(state)

    if "nodes" not in trimmed_state:
        return trimmed_state

    for node in trimmed_state["nodes"]:
        if "options" in node:
            for option in node["options"]:
                if "content" in option and len(option["content"]) > char_limit:
                    option["content"] = (
                        option["content"][: char_limit // 2]
                        + "..."
                        + option["content"][-char_limit // 2 :]
                    )
    return trimmed_state
