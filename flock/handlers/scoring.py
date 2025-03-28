"""Handlers for scoring operations"""

from typing import List, Optional

from flock.handlers.base import create_handler
from flock.type_defs.operations import (
    ScoreLogEntry,
    ScoreLogParams,
    ScoreOutput,
    ScoreParams,
)
from flock.type_defs.processing import ProcessingMode


async def score_hooks(params: ScoreParams, deps: Optional[dict]) -> ScoreOutput:
    hooks_client = deps["hooks_client"]
    action_data = {
        "type": "score",
        "args": {},
    }
    await hooks_client.action(action_data)
    raw_result = await hooks_client.score()

    score_output = ScoreOutput(message=raw_result.dict())
    return score_output


async def score_mock(params: ScoreParams, deps: Optional[dict]) -> ScoreOutput:
    """Score handler for mock mode"""
    mock_result = ScoreOutput(message={"score": 0.75, "message": "Scoring completed"})
    return mock_result


async def score_log_hooks(
    params: ScoreLogParams, deps: Optional[dict]
) -> List[ScoreLogEntry]:
    hooks_client = deps["hooks_client"]
    action_data = {
        "type": "score_log",
        "args": {},
    }
    await hooks_client.action(action_data)
    result = await hooks_client.scoreLog()
    return [ScoreLogEntry(**entry.dict()) for entry in result]


async def score_log_mock(
    params: ScoreLogParams, deps: Optional[dict]
) -> List[ScoreLogEntry]:
    mock_entries = [
        {
            "timestamp": "2024-01-01T00:00:00Z",
            "score": 0.5,
            "max_score": 1.0,
            "message": "Initial score",
        },
        {
            "timestamp": "2024-01-01T00:01:00Z",
            "score": 0.75,
            "max_score": 1.0,
            "message": "Improved score",
        },
    ]
    return [ScoreLogEntry(**entry) for entry in mock_entries]


score_handlers = {
    ProcessingMode.HOOKS: create_handler("score", score_hooks),
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("score", score_mock),
}

score_log_handlers = {
    ProcessingMode.HOOKS: create_handler("score_log", score_log_hooks),
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("score_log", score_log_mock),
}
