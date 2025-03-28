"""Handler for saving state snapshots"""

import difflib
import json
from datetime import datetime
from typing import Optional

from flock.config import STATES_DIR
from flock.handlers.base import create_handler
from flock.logger import logger
from flock.type_defs.operations import (
    SaveStateOutput,
    SaveStateParams,
)
from flock.type_defs.processing import ProcessingMode


async def hooks_save_state(
    params: SaveStateParams, deps: Optional[dict]
) -> SaveStateOutput:
    hooks_client = deps["hooks_client"]
    response = await hooks_client.save_state(params.state)
    return SaveStateOutput(
        status="success", message=str(response), snapshot_path="vivaria"
    )


async def local_save_state(
    params: SaveStateParams, deps: Optional[dict]
) -> SaveStateOutput:
    """Save a state snapshot"""
    try:
        state_id = params.state_id
        state = params.state
        timestamp = params.timestamp or datetime.utcnow().isoformat()

        # Create workflow-specific directory
        workflow_dir = STATES_DIR / state_id
        snapshots_dir = workflow_dir / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        # Create snapshot file with timestamp
        snapshot_file = snapshots_dir / f"state_{timestamp}.json"

        # Load existing state if available
        state_file = STATES_DIR / f"{state_id}.json"
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    existing_state = json.dumps(json.load(f), indent=2).splitlines()
                new_state = json.dumps(state, indent=2).splitlines()

                # Generate diff
                diff = list(
                    difflib.unified_diff(
                        existing_state,
                        new_state,
                        fromfile=f"previous_{state_id}",
                        tofile=f"new_{state_id}",
                        lineterm="",
                    )
                )

                if diff:
                    logger.debug("State changes:")
                    for line in diff:
                        logger.debug(line)
                else:
                    logger.debug("No changes in state")
            except Exception as e:
                logger.debug(f"Error generating state diff: {e}")

        # Save new state
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

        # Save snapshot
        with open(snapshot_file, "w") as f:
            json.dump(state, f, indent=2)

        return SaveStateOutput(
            status="success",
            message=f"State snapshot saved to {snapshot_file}",
            snapshot_path=str(snapshot_file),
        )
    except Exception as e:
        error_msg = f"Error saving state snapshot: {str(e)}"
        logger.error(error_msg)
        return SaveStateOutput(
            status="error",
            message=error_msg,
            snapshot_path="",
        )


handlers = {
    ProcessingMode.HOOKS: create_handler("save_state", hooks_save_state),
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("save_state", local_save_state),
}
