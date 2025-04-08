"""Handlers for python operation"""

from typing import Optional

from flock.handlers.base import create_handler
from flock.type_defs.operations import PythonOutput, PythonParams
from flock.type_defs.processing import ProcessingMode


async def python_middleman(params: PythonParams, deps: Optional[dict]) -> PythonOutput:
    """Python handler for middleman mode"""
    simulator = deps["simulator"]
    try:
        result = await simulator["simulate_command"](simulator, params.code, "python")
        if isinstance(result, dict):
            return PythonOutput(
                output=str(result.get("output", "")), error=result.get("error")
            )
        return result
    except Exception as e:
        return PythonOutput(output="", error=str(e))


async def python_hooks(params: PythonParams, deps: Optional[dict]) -> PythonOutput:
    """Python handler for hooks mode"""
    hooks_client = deps["hooks_client"]

    action_data = {
        "type": "python",
        "args": {"code": params.code},
    }
    await hooks_client.action(action_data)

    # Execute the Python code
    result = await hooks_client.run_python(params.code, params.timeout)
    return PythonOutput(output=result, error=None)


handlers = {
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("python", python_middleman),
    ProcessingMode.HOOKS: create_handler("python", python_hooks),
}
