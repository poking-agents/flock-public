"""Execute workflow phases"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

from logger import logger


async def execute_phase(
    phase_name: str, state_id: str, previous_operations: Dict[str, Any]
) -> None:
    """Execute a workflow phase with the given state and previous operations"""
    previous_operations_json = json.dumps(previous_operations)
    absolute_path = Path(__file__).parent.parent / f"{phase_name}"

    logger.debug(f"[{state_id}][{phase_name}] {'=' * 40}")
    logger.debug(f"[{state_id}][{phase_name}] Starting phase execution")
    logger.debug(f"[{state_id}][{phase_name}] Phase path: {str(absolute_path)}")
    logger.debug(
        f"[{state_id}][{phase_name}] Previous results: {json.dumps(previous_operations, indent=2)}"
    )

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(absolute_path),
        state_id,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate(input=previous_operations_json.encode())

    if stdout:
        logger.debug(f"[{state_id}][{phase_name}] stdout: {stdout.decode()}")

    if proc.returncode != 0:
        error_msg = f"Phase {phase_name} failed with exit code {proc.returncode}"
        if stderr:
            error_msg += f"\nstderr: {stderr.decode()}"
        logger.error(f"[{state_id}][{phase_name}] {error_msg}")
        raise Exception(error_msg)

    logger.debug(f"[{state_id}][{phase_name}] Phase completed successfully")
