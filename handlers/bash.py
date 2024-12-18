import asyncio
import os
from pathlib import Path
from typing import Optional

from handlers.base import create_handler
from logger import logger
from type_defs.operations import BashOutput, BashParams
from type_defs.processing import ProcessingMode


async def bash_middleman(params: BashParams, deps: Optional[dict]) -> BashOutput:
    """Bash handler for middleman mode"""
    simulator = deps["simulator"]
    try:
        result = await simulator["simulate_command"](simulator, params.command, "bash")
        if isinstance(result, dict):
            return BashOutput(
                stdout=str(result.get("stdout", "")),
                stderr=str(result.get("stderr", "")),
                status=result.get("returncode", 0),
            )
        return result
    except Exception as e:
        return BashOutput(stdout="", stderr=f"Simulation error: {str(e)}", status=1)


async def bash_hooks(params: BashParams, deps: Optional[dict]) -> BashOutput:
    """Bash handler for hooks mode with per-agent state tracking using the current working directory."""
    command = params.command
    timeout = params.timeout or 60
    agent_id = getattr(params, "agent_id", None)

    # Ensure existence of subagent environment directory if agent_id is provided
    if agent_id:
        env_dir = Path("subagents") / agent_id / ".cache"
        env_dir.mkdir(parents=True, exist_ok=True)
        env_dir_path = str(env_dir)
    else:
        # Use a general environment directory for the main agent
        env_dir = Path(os.getenv("TEST_ENVIRONMENT", str(Path.home() / ".agent_env")))
        env_dir.mkdir(parents=True, exist_ok=True)
        env_dir_path = str(env_dir)

    # Construct the shell command
    # Directly run the command in agent_id directory if agent_id is provided
    if agent_id:
        working_dir_path = str(Path("subagents") / agent_id)
        full_command = f"cd {working_dir_path} && {command}"

    logger.debug(
        f"[{'Subagent: ' + agent_id if agent_id else 'Main Agent'}] Running bash command: {full_command}"
    )

    try:
        # Start the subprocess
        proc = await asyncio.create_subprocess_shell(
            full_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable="/bin/bash",
        )

        # Wait for the process to finish or timeout
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            # If the command times out, kill it and return code 124
            proc.kill()
            return BashOutput(
                stdout="",
                stderr=f"Command '{command}' timed out after {timeout} seconds.",
                status=124,
            )

        # Read stdout and stderr from the process
        stdout_data = await proc.stdout.read() if proc.stdout else b""
        stderr_data = await proc.stderr.read() if proc.stderr else b""
        stdout_content = stdout_data.decode("utf-8", errors="ignore")
        stderr_content = stderr_data.decode("utf-8", errors="ignore")

        # Use the process's return code
        return_code = proc.returncode if proc.returncode is not None else 1

        # Return the results
        return BashOutput(
            stdout=stdout_content.strip(),
            stderr=stderr_content.strip(),
            status=return_code,
        )
    except Exception as e:
        logger.error(f"Error in bash_hooks: {str(e)}", exc_info=True)
        return BashOutput(stdout="", stderr=str(e), status=1)


handlers = {
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("bash", bash_middleman),
    ProcessingMode.HOOKS: create_handler("bash", bash_hooks),
}
