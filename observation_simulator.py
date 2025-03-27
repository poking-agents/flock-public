"""Simulator for operation outputs"""

import json
from textwrap import dedent
from typing import Any, Dict, List, Union

from logger import logger
from middleman_client import get_credentials, post_completion
from type_defs.operations import (
    BashOutput,
    PythonOutput,
)


def create_simulator(
    model: str = "gpt-4o-mini",
    context: str = None,
) -> Dict[str, Any]:
    """Create a simulator with the given settings"""
    base_url, api_key = get_credentials()
    context = (
        context
        or dedent(
            """
        You are simulating an interactive session. 
        Given the following history of commands and their outputs, 
        provide the most likely output for the new command. 
        If the command is invalid or would cause an error, provide an appropriate error message.
        Assume that the most common apt & pip packages are installed.
        Respond only with the simulated output, without any additional explanation, wrapped in backticks.
    """  # noqa: E501
        ).strip()
    )

    history: List[Dict[str, str]] = []
    return {
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "context": context,
        "history": history,
        "simulate_command": simulate_command,
    }


def process_response(response: Dict[str, Any]) -> str:
    """Extract completion from Middleman API response"""
    if "outputs" in response and response["outputs"]:
        return response["outputs"][0]["completion"]
    elif "completion" in response:
        return response["completion"]
    else:
        raise ValueError("No completion found in response")


async def simulate_command(
    sim_state: Dict, command: str, tool: str
) -> Union[BashOutput, PythonOutput]:
    """
    Simulate the output of a bash or python command using the Middleman API.

    Args:
        sim_state: Simulator state dictionary
        command: The command to simulate
        tool: Either "bash" or "python"

    Returns:
        Simulated command result
    """
    # TODO: require function use here
    messages = [
        {
            "role": "system",
            "content": dedent(
                """
            You are simulating a Linux command execution environment.
            For bash commands, respond with a JSON object containing:
            - stdout: command output
            - stderr: error output if any
            - returncode: 0 for success, non-zero for errors
            
            For Python code, respond with a JSON object containing:
            - output: execution output
            - error: error message if any
            
            Assume that common apt & pip packages are installed,
            that the initial directory is /home/agent, and that resources needed by the task are available.
            Format the response as a single-line JSON string without any markdown formatting or explanation.
            Example bash: {"stdout": "file1.txt\\nfile2.txt", "stderr": "", "returncode": 0} 
            Example python: {"output": "Hello, world!", "error": null}
        """  # noqa: E501
            ).strip(),
        },
        {"role": "user", "content": f"Simulate this {tool} command: {command}"},
    ]

    models = [sim_state["model"], "gpt-4o"]
    max_retries = 5
    last_error = BaseException()

    for model in models:
        for attempt in range(max_retries):
            try:
                response = await post_completion(
                    messages=messages,
                    model=model,
                    temp=0.7,
                    n=1,
                )
                output = process_response(response)

                if tool == "bash":
                    try:
                        result = json.loads(output)
                        if all(k in result for k in ["stdout", "stderr", "returncode"]):
                            return BashOutput(
                                stdout=result["stdout"],
                                stderr=result["stderr"],
                                status=result["returncode"],
                            )
                        else:
                            raise ValueError("Missing required fields in JSON response")
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.debug(
                            "Failed to parse response as bash result JSON (attempt "
                            f"{attempt + 1}): {str(e)}"
                        )
                        if attempt == max_retries - 1 and model == models[-1]:
                            return BashOutput(stdout=output, stderr="", status=0)
                        continue
                elif tool == "python":
                    try:
                        result = json.loads(output)
                        if "output" in result:
                            return PythonOutput(
                                output=result["output"], error=result.get("error")
                            )
                        else:
                            raise ValueError("Missing required fields in JSON response")
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.debug(
                            "Failed to parse response as python result JSON (attempt "
                            f"{attempt + 1}): {str(e)}"
                        )
                        if attempt == max_retries - 1 and model == models[-1]:
                            return PythonOutput(output=output, error=None)
                        continue
                else:
                    raise ValueError(f"Unsupported tool type: {tool}")
            except Exception as e:
                logger.error(f"Error simulating command: {str(e)}")
                last_error = e
                continue
    raise last_error
