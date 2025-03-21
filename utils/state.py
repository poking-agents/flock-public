"""State management utilities"""

import json
from typing import Any, Dict, Optional, Type
import copy

from pydantic import BaseModel

from config import STATES_DIR


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
    state_char_limit = state.get("context_trimming_threshold", 8_000)
    state = trim_state(state, state_char_limit)
    STATES_DIR.mkdir(exist_ok=True)
    state_file = STATES_DIR / f"{state_id}.json"
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def truncate_string(input: str, char_limit: int) -> str:
    return (
        input[: char_limit // 2]
        + "... [truncated due to the content being too long] ..."
        + input[-char_limit // 2 :]
    )


def trim_state(state: Dict[str, Any], char_limit: int) -> Dict[str, Any]:
    # Create a deep copy of the state to avoid modifying the original
    if "nodes" not in state or "previous_results" not in state:
        return state

    for node in state["nodes"]:
        if "options" in node:
            for option in node["options"]:
                if "content" in option and len(option["content"]) > char_limit:
                    option["content"] = truncate_string(option["content"], char_limit)

    for results in state["previous_results"]:
        for result in results:
            if result["type"] == "bash":
                for field in ["stderr", "stdout"]:
                    if len(result["result"][field]) > char_limit:
                        result["result"][field] = truncate_string(
                            result["result"][field], char_limit
                        )
            elif result["type"] == "python":
                for field in ["error", "output"]:
                    if (
                        result["result"][field]
                        and len(result["result"][field]) > char_limit
                    ):
                        result["result"][field] = truncate_string(
                            result["result"][field], char_limit
                        )

    return state
