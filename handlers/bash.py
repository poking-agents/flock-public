"""Handlers for bash operation"""

import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import aiofiles

from handlers.base import create_handler
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
    """Bash handler for hooks mode with per-agent state tracking"""
    hooks_client = deps["hooks_client"]
    command = params.command
    timeout = params.timeout
    agent_id = getattr(params, "agent_id", None)

    action_data = {
        "type": "run_bash",
        "args": {
            "command": command,
        },
    }
    await hooks_client.action(action_data)

    # Set up agent-specific cache directory
    if agent_id:
        cache_dir = Path("subagents") / agent_id / ".cache"
    else:
        cache_dir = Path.home() / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    last_dir_file = cache_dir / ".last_dir"
    last_env_file = cache_dir / ".last_env"

    # Initialize directory tracking if not exists
    if not last_dir_file.exists():
        # Start in agent's directory if it exists
        if agent_id:
            agent_dir = Path("subagents") / agent_id
            agent_dir.mkdir(parents=True, exist_ok=True)
            with last_dir_file.open("w") as f:
                f.write(str(agent_dir))
        else:
            with last_dir_file.open("w") as f:
                f.write(str(Path.cwd()))

    # Initialize environment tracking if not exists
    if not last_env_file.exists():
        env = subprocess.check_output(["bash", "-c", "declare -p"], text=True)
        with last_env_file.open("w") as f:
            f.write(env)

    command_counter = int(time.time() * 1000)
    stdout_path = f"/tmp/bash_stdout_{agent_id or 'default'}_{command_counter}"
    stderr_path = f"/tmp/bash_stderr_{agent_id or 'default'}_{command_counter}"
    returncode_path = f"/tmp/bash_returncode_{agent_id or 'default'}_{command_counter}"

    full_command = f"""cd $( cat {last_dir_file} ) >/dev/null; 
        source {last_env_file} 2>/dev/null && 
        export TQDM_DISABLE=1 && 
        ( {command}
        echo $? > {returncode_path}; 
        pwd > {last_dir_file}; 
        declare -p > {last_env_file} ) > {stdout_path} 2> {stderr_path}"""

    try:
        proc = await asyncio.create_subprocess_exec(
            "bash",
            "-c",
            full_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            returncode = proc.returncode
            try:
                async with aiofiles.open(returncode_path, "r") as f:
                    returncode = int((await f.read()).strip())
            except Exception:
                pass
            try:
                async with aiofiles.open(stdout_path, "r") as f:
                    stdout_content = await f.read()
                async with aiofiles.open(stderr_path, "r") as f:
                    stderr_content = await f.read()
            except Exception as e:
                stdout_content = stdout.decode() if stdout else ""
                stderr_content = (
                    stderr.decode() if stderr else f"Error reading output: {str(e)}"
                )
            return BashOutput(
                stdout=stdout_content, stderr=stderr_content, status=returncode
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
                stdout, stderr = await proc.communicate()
                return BashOutput(
                    stdout=stdout.decode() if stdout else "",
                    stderr=f"""{stderr.decode() if stderr else ""}
Command timed out after {timeout} seconds.""",
                    status=124,
                )
            except ProcessLookupError:
                return BashOutput(
                    stdout="",
                    stderr="Process ended before it could be killed",
                    status=125,
                )
    except Exception as e:
        return BashOutput(
            stdout="", stderr=f"Error executing command: {str(e)}", status=1
        )
    finally:
        for path in [stdout_path, stderr_path, returncode_path]:
            try:
                os.remove(path)
            except Exception:
                pass


handlers = {
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("bash", bash_middleman),
    ProcessingMode.HOOKS: create_handler("bash", bash_hooks),
}
