import json
import re
from functools import partial
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple, Union

from type_defs.base import Node, Option
from type_defs.operations import (
    BaseOperationRequest,
    BashOutput,
    BashParams,
    BashRequest,
    OperationMetadata,
    OperationResult,
    PythonOutput,
    PythonParams,
    PythonRequest,
    ScoreLogEntry,
    ScoreLogParams,
    ScoreLogRequest,
    ScoreOutput,
    ScoreParams,
    ScoreRequest,
    SubmissionOutput,
    SubmissionParams,
    SubmissionRequest,
)
from type_defs.states import DEFAULT_TIMEOUT, AgentState, ModularState, triframeState

submit = {
    "name": "submit",
    "description": (
        "Submit your final answer to the task. On some tasks, your score will be "
        "determined by this answer. On other tasks, submitting indicates that you have "
        "finished your work on some artifact, like a file on the server. If you the "
        "task is scored based on a file, make sure that you have written the correct "
        "content to the file before submitting."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "The final answer to submit",
            },
        },
        "required": ["answer"],
    },
}

submit_backticks = """```submit
[your final answer to the task at hand]
```
Note: This function will submit your final answer to the task. On some tasks, your score
 will be determined by this answer. On other tasks, submitting indicates that you have 
finished your work on some artifact, like a file on the server. If you the task is 
scored based on a file, make sure that you have written the correct content to the file 
before submitting."""

bash = {
    "name": "run_bash",
    "description": (
        "Run a bash command on the server. This does not support interactive commands, "
        "like 'vim'. Changing the directory with 'cd' will affect subsequent commands, "
        "but 'ssh' will not keep the connection open. If you are working with code in "
        "a file, consider using a heredoc (EOF) to write to the file."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute",
            },
        },
        "required": ["command"],
    },
}

bash_backticks = """```run_bash
[bash command to be executed in the VM]
```
Note: interactive commands (like vim and nano) are not supported by the scaffolding. 
Use '&' to run long-running commands in the background.
"""

python = {
    "name": "run_python",
    "description": (
        "Run Python code on the server, in an session that persists between calls. "
        "This means that variables and functions defined in one call will be available "
        "in subsequent calls."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute",
            },
        },
        "required": ["code"],
    },
}

python_backticks = """```run_python
[python code to be executed in an interactive python session]
```"""

score = {
    "name": "score",
    "description": (
        "On some tasks, this will return a score to you. "
        "On all tasks, these mid-run scores will be used to evaluate your progress. "
        "A score of NaN means that your submission is invalid. "
        "Call this command when you have made meaningful progress."
    ),
    "parameters": {},
}

score_backticks = (
    "```score\n```\n Note: "
    "this function call has no parameter, thus nothing goes inside the backticks. On "
    "some tasks, this will return a score to you. On all tasks, these mid-run scores "
    "will be used to evaluate your progress. A score of NaN means that your submission "
    "is invalid. Call this command when you have made meaningful progress."
)

score_log = {
    "name": "score_log",
    "description": "Get the history of your scores.",
    "parameters": {},
}

score_log_backticks = """```score_log
```
Note: this function call has no parameter, thus nothing goes inside the backticks. 
This function call returns the history of your scores. 
"""

set_timeout = {
    "name": "set_timeout",
    "description": (
        "Change the timeout used for bash and python commands. If you encounter "
        "'PythonExecTimeoutException' or 'Exit code: 124', consider setting a higher "
        f"timeout value. The default is {DEFAULT_TIMEOUT} seconds. Alternatively, you "
        "can use the run_bash command to run a process in the background. (If you do "
        "this, keep in mind that the process will use resources [e.g. memory] until "
        "it completes)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "timeout": {
                "type": "integer",
                "description": "The new timeout in seconds",
            },
        },
        "required": ["timeout"],
    },
}

set_timeout_backticks = """```set_timeout
[number of seconds to set the bash and python timeout to]
```"""

STANDARD_FUNCTION_VALIDATIONS = {
    "run_python": ("code", str),
    "run_bash": ("command", str),
    "submit": ("answer", str),
    "set_timeout": ("timeout", int),
    "score": (),
    "score_log": (),
}

STANDARD_TOOL_OUTPUT_TYPES_TO_NAMES = {
    BashOutput: "run_bash",
    PythonOutput: "run_python",
    SubmissionOutput: "submit",
    ScoreOutput: "score",
    List[ScoreLogEntry]: "score_log",
}


def get_standard_function_definitions(
    state: Union[triframeState, ModularState],
) -> List[Dict[str, Any]]:
    """Return a list of function definitions for the triframe agent"""
    intermediate_scoring = state.settings.intermediate_scoring
    standard_functions = [bash, python, set_timeout]
    if intermediate_scoring:
        standard_functions.append(score)
        standard_functions.append(score_log)
    else:
        standard_functions.append(submit)
    return standard_functions


def get_standard_backticks_function_definitions(
    state: Union[triframeState, ModularState],
) -> str:
    standard_functions = "\n".join(
        [bash_backticks, python_backticks, set_timeout_backticks]
    )
    intermediate_scoring = state.settings.intermediate_scoring
    if intermediate_scoring:
        standard_functions += "\n".join([score_backticks, score_log_backticks])
    else:
        standard_functions += "\n".join([submit_backticks])
    return standard_functions


def parse_backticks_function_names(completion: str) -> List[Dict[str, Any]]:
    function_names = re.findall(r"```(\w+)", completion)
    return function_names


def parse_backticks_function_call(
    function_name: str,
    completion: str,
    func_name_to_args: Dict[str, Tuple[str, type]] = STANDARD_FUNCTION_VALIDATIONS,
) -> Dict[str, Any] | None:
    if f"```{function_name}" not in completion:
        return None
    function_args = completion.split(f"```{function_name}")[1].split("```")[0]
    function_args = function_args.strip()

    # fix common generation mistakes
    if function_name == "python":
        function_name = "run_python"
    elif function_name == "bash":
        function_name = "run_bash"

    if function_name not in func_name_to_args:
        return None
    if not func_name_to_args[function_name]:
        return {"name": function_name, "arguments": json.dumps({})}

    arg_name, arg_type = func_name_to_args[function_name]
    if arg_type is not None and not function_args:
        return None
    try:
        function_args = {arg_name: arg_type(function_args)}
        return {"name": function_name, "arguments": json.dumps(function_args)}
    except ValueError:
        return None


def parse_backticks_json(completion: str) -> Dict[str, Any] | None:
    if "```json" not in completion:
        return None
    json_str = completion.split("```json")[1].split("```")[0]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def remove_code_blocks(text: str) -> str:
    pattern = r"```[^`]*```"
    cleaned_text = re.sub(pattern, "", text)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    return cleaned_text.strip()


def combine_function_call_and_content(
    function_call: Dict[str, Any], content: str
) -> str:
    args = list(json.loads(function_call["arguments"]).values())[0]
    function_call_str = f"```{function_call['name']}\n{args}\n```"
    return f"{content}\n\n{function_call_str}"


def validate_function_call(
    function_call: Optional[Dict[str, Any]],
    additional_validations: Optional[Dict[str, Tuple[str, type]]] = None,
) -> bool:
    """
    Validates function calls with configurable additional validation rules.

    Args:
        function_call: The function call to validate
        additional_validations: Dictionary of additional function validations
            in the format {function_name: (required_arg, arg_type)}
    """
    if not function_call or not isinstance(function_call, dict):
        return False
    function_name = function_call.get("name")
    if not function_name:
        return False

    if (
        function_name in STANDARD_FUNCTION_VALIDATIONS
        and STANDARD_FUNCTION_VALIDATIONS[function_name] == ()
    ):
        return True

    try:
        arguments = function_call.get("arguments", "{}")
        args = json.loads(arguments) if isinstance(arguments, str) else arguments

        # Combine base validations with any additional ones
        validations = STANDARD_FUNCTION_VALIDATIONS.copy()
        if additional_validations:
            validations.update(additional_validations)

        if function_name not in validations:
            return False

        required_arg, arg_type = validations[function_name]
        return required_arg in args and isinstance(args[required_arg], arg_type)

    except (json.JSONDecodeError, AttributeError, TypeError):
        return False


def enforce_output_limit(output_limit: int, output: str) -> str:
    if len(output) > output_limit:
        half = output_limit // 2
        starts_with = output[:half]
        ends_with = output[-half:]
        return dedent(
            f"""This output was too long to include in its entirety.
        The start and end of the output are shown below.
        {starts_with}
        [output truncated]
        {ends_with}"""
        )
    return output


def format_tool_output(output_limit: int, operation_result: Dict[str, Any]) -> str:
    enforce_limit = partial(enforce_output_limit, output_limit)

    if isinstance(operation_result, BashOutput):
        parts = []
        parts.append(enforce_limit(operation_result.stdout))
        if operation_result.stderr:
            parts.append(f"Error: {enforce_limit(operation_result.stderr)}")
        if operation_result.status and operation_result.status != 0:
            parts.append(f"Exit code: {operation_result.status}")
        return "\n".join(parts)
    elif isinstance(operation_result, PythonOutput):
        parts = [enforce_limit(operation_result.output)]
        if operation_result.error:
            parts.append(f"Error: {enforce_limit(operation_result.error)}")
        return "\n".join(parts)
    elif isinstance(operation_result, ScoreOutput):
        return enforce_limit(str(operation_result.message))
    elif isinstance(operation_result, List[ScoreLogEntry]):
        entries = []
        for entry in operation_result:
            entries.append(entry.model_dump())
        return enforce_limit("\n---\n".join(entries))
    else:
        return enforce_limit(json.dumps(operation_result))


def get_tool_output_name(
    operation_result: Dict[str, Any],
    tool_output_to_name: Dict[type, str] = STANDARD_TOOL_OUTPUT_TYPES_TO_NAMES,
) -> str:
    if type(operation_result) not in tool_output_to_name.keys():
        raise ValueError(
            f"Unable to get name for unknown tool output type: {type(operation_result)}"
        )
    return tool_output_to_name[type(operation_result)]


def get_tool_operation_result(last_update: List[OperationResult]) -> Dict[str, Any]:
    tool_result = next(
        (
            op
            for op in last_update
            if op.type in ["bash", "python", "submit", "score", "score_log"]
        ),
        None,
    )
    if not tool_result:
        raise ValueError("No tool operation found in last update")
    return tool_result.result


def create_standard_tool_operation(
    tool_name: str, tool_args: dict, metadata: OperationMetadata
) -> BaseOperationRequest | None:
    if tool_name == "submit":
        return SubmissionRequest(
            type="submit",
            params=SubmissionParams(submission=tool_args["answer"]),
            metadata=metadata,
        )
    elif tool_name == "run_bash":
        return BashRequest(
            type="bash",
            params=BashParams(command=tool_args["command"]),
            metadata=metadata,
        )
    elif tool_name == "run_python":
        return PythonRequest(
            type="python",
            params=PythonParams(code=tool_args["code"]),
            metadata=metadata,
        )
    elif tool_name == "score":
        return ScoreRequest(type="score", params=ScoreParams(), metadata=metadata)
    elif tool_name == "score_log":
        return ScoreLogRequest(
            type="score_log", params=ScoreLogParams(), metadata=metadata
        )
    else:
        return None


def handle_set_timeout(state: AgentState, tool_args: dict) -> AgentState:
    """Handle the set_timeout tool operation"""
    try:
        state.timeout = int(tool_args["timeout"])
        state.nodes.append(
            Node(
                source="tool_output",
                options=[
                    Option(
                        content=f"Timeout set to {state.timeout}", name="set_timeout"
                    )
                ],
            )
        )
    except (KeyError, ValueError):
        state.nodes.append(
            Node(
                source="warning",
                options=[
                    Option(
                        content=(
                            "Invalid set_timeout function call, timeout remains ",
                            f"{state.timeout} seconds",
                        )
                    )
                ],
            )
        )
    state.update_usage()
    return state
