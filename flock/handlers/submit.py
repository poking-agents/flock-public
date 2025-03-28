"""Handlers for submit operation"""

import json
import os
from datetime import datetime
from typing import Optional

from flock.handlers.base import create_handler
from flock.logger import logger
from flock.type_defs.operations import (
    SubmissionOutput,
    SubmissionParams,
)
from flock.type_defs.processing import ProcessingMode


async def submit_middleman(
    params: SubmissionParams, deps: Optional[dict]
) -> SubmissionOutput:
    """Submit handler for middleman mode"""
    try:
        submission_text = params.submission

        # Create submissions directory if it doesn't exist
        os.makedirs("submissions", exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"submissions/submission_{timestamp}.json"

        # Save submission
        submission_data = {
            "content": submission_text,
            "timestamp": timestamp,
        }

        with open(filename, "w") as f:
            json.dump(submission_data, f, indent=2)

        logger.info(f"Submission saved to {filename}")

        return SubmissionOutput(
            status="success",
            message=f"Submission saved to {filename}",
            submission_id=timestamp,
        )

    except Exception as e:
        error_msg = f"Error handling submission: {str(e)}"
        logger.error(error_msg)
        return SubmissionOutput(status="error", message=error_msg, submission_id=None)


async def submit_hooks(
    params: SubmissionParams, deps: Optional[dict]
) -> SubmissionOutput:
    """Submit handler for hooks mode"""
    hooks_client = deps["hooks_client"]
    submission_text = params.submission

    try:
        result = await hooks_client.submit(str(submission_text))

        # Log submission
        await hooks_client.log(f"Submission sent: {submission_text[:100]}...")

        return SubmissionOutput(
            status="success",
            message="Submission sent through hooks",
            submission_id=result.get("id"),
        )

    except Exception as e:
        error_msg = f"Error in hooks submission: {str(e)}"
        logger.error(error_msg)
        return SubmissionOutput(status="error", message=error_msg, submission_id=None)


handlers = {
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("submit", submit_middleman),
    ProcessingMode.HOOKS: create_handler("submit", submit_hooks),
}
