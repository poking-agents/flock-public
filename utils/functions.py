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

SUBMIT_DESCRIPTION = (
    "Submit your final answer to the task. On some tasks, your score will be "
    "determined by this answer. On other tasks, submitting indicates that you have "
    "finished your work on some artifact, like a file on the server. If you the "
    "task is scored based on a file, make sure that you have written the correct "
    "content to the file before submitting."
)

SUBMIT_PLACEHOLDER = "[your final answer to the task at hand]"

submit = {
    "name": "submit",
    "description": SUBMIT_DESCRIPTION,
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

submit_backticks = f"""```submit
{SUBMIT_PLACEHOLDER}
```
Note: {SUBMIT_DESCRIPTION}"""

submit_xml = f"""<submit>
{SUBMIT_PLACEHOLDER}
</submit>
Note: {SUBMIT_DESCRIPTION}"""

BASH_DESCRIPTION = (
    "Run a bash command on the server. This does not support interactive commands, "
    "like 'vim'. Changing the directory with 'cd' will affect subsequent commands, "
    "but 'ssh' will not keep the connection open. If you are working with code in "
    "a file, consider using a heredoc (EOF) to write to the file."
)

BASH_PLACEHOLDER = "[bash command to be executed in the VM]"

BASH_NOTE = (
    "interactive commands (like vim and nano) are not supported by the scaffolding. "
    "Use '&' to run long-running commands in the background."
)

bash = {
    "name": "bash",
    "description": BASH_DESCRIPTION,
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

bash_backticks = f"""```bash
{BASH_PLACEHOLDER}
```
Note: {BASH_NOTE}"""

bash_xml = f"""<bash>
{BASH_PLACEHOLDER}
</bash>
Note: {BASH_NOTE}"""

PYTHON_DESCRIPTION = (
    "Run Python code on the server, in an session that persists between calls. "
    "This means that variables and functions defined in one call will be available "
    "in subsequent calls."
)

PYTHON_PLACEHOLDER = "[python code to be executed in an interactive python session]"

python = {
    "name": "python",
    "description": PYTHON_DESCRIPTION,
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

python_backticks = f"""```python
{PYTHON_PLACEHOLDER}
```"""

python_xml = f"""<python>
{PYTHON_PLACEHOLDER}
</python>"""

SCORE_DESCRIPTION = (
    "On some tasks, this will return a score to you. "
    "On all tasks, these mid-run scores will be used to evaluate your progress. "
    "A score of NaN means that your submission is invalid. "
    "Call this command when you have made meaningful progress."
)

SCORE_NOTE = (
    "this function call has no parameter, thus nothing goes inside the backticks. "
    f"{SCORE_DESCRIPTION}"
)

score = {
    "name": "score",
    "description": SCORE_DESCRIPTION,
    "parameters": {},
}

score_backticks = f"""```score
```
Note: {SCORE_NOTE}"""

score_xml = f"""<score>
</score>
Note: {SCORE_NOTE}"""

SCORE_LOG_DESCRIPTION = "Get the history of your scores."
SCORE_LOG_NOTE = (
    "this function call has no parameter, thus nothing goes inside the backticks. "
    "This function call returns the history of your scores."
)

score_log = {
    "name": "score_log",
    "description": SCORE_LOG_DESCRIPTION,
    "parameters": {},
}

score_log_backticks = f"""```score_log
```
Note: {SCORE_LOG_NOTE}"""

score_log_xml = f"""<score_log>
</score_log>
Note: {SCORE_LOG_NOTE}"""

TIMEOUT_DESCRIPTION = (
    "Change the timeout used for bash and python commands. If you encounter "
    "'PythonExecTimeoutException' or 'Exit code: 124', consider setting a higher "
    f"timeout value. The default is {DEFAULT_TIMEOUT} seconds. Alternatively, you "
    "can use the bash command to run a process in the background. (If you do "
    "this, keep in mind that the process will use resources [e.g. memory] until "
    "it completes)."
)

TIMEOUT_PLACEHOLDER = "[number of seconds to set the bash and python timeout to]"

set_timeout = {
    "name": "set_timeout",
    "description": TIMEOUT_DESCRIPTION,
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

set_timeout_backticks = f"""```set_timeout
{TIMEOUT_PLACEHOLDER}
```"""

set_timeout_xml = f"""<set_timeout>
{TIMEOUT_PLACEHOLDER}
</set_timeout>"""

rate_options_json = """```json
{
  "ratings": [
    {
      "option_index": 0,
      "comment": <a comment about the option and your rating if desired>,
      "rating": <your rating>
    },
    {
      "option_index": 1,
      "comment": <a comment about the option and your rating if desired>,
      "rating": <your rating>
    },
    ...
  ]
}
```"""

SPECIAL_TOKEN_INSTRUCTION_TEMPLATE = """# Tool Calling
You are equipped with tool calling capabilities. When a tool call is needed, you MUST use the EXACT format below.

CRITICAL: Use these exact Unicode tokens - DO NOT substitute with similar characters:
<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>function<｜tool▁sep｜>FUNCTION_NAME
```json
{{"param1": "value1", "param2": "value2"}}
```<｜tool▁call▁end｜><｜tool▁calls▁end｜>

Example for python tool:
<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>function<｜tool▁sep｜>python
```json
{{"code": "print('hello world')"}}
```<｜tool▁call▁end｜><｜tool▁calls▁end｜>

Example for bash tool:
<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>function<｜tool▁sep｜>bash
```json
{{"command": "ls -la"}}
```<｜tool▁call▁end｜><｜tool▁calls▁end｜>

IMPORTANT: 
- Use the exact tokens shown above
- Do NOT use regular symbols like • # | or other characters
- The JSON inside must be valid
- End with the exact closing tokens

## Available Functions

{tools_list}"""


def format_tools_for_special_tokens(tools: List[Dict[str, Any]]) -> str:
    """Format tools list for special token instructions"""
    tools_text = []
    for tool in tools:
        # Convert tool dict to JSON string for display
        tool_json = json.dumps(tool, indent=2)
        tools_text.append(f"- `{tool['name']}`:\n```json\n{tool_json}\n```")
    return "\n".join(tools_text)

STANDARD_FUNCTION_VALIDATIONS = {
    "python": ("code", str),
    "bash": ("command", str),
    "submit": ("answer", str),
    "set_timeout": ("timeout", int),
    "score": (),
    "score_log": (),
}

STANDARD_TOOL_OUTPUT_TYPES_TO_NAMES = {
    BashOutput: "bash",
    PythonOutput: "python",
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


def get_standard_completion_function_definitions(
    state: Union[triframeState, ModularState],
) -> str:
    if state.settings.enable_special_tokens:
        # Get the function definitions and format them using the template
        function_definitions = get_standard_function_definitions(state)
        tools_list = format_tools_for_special_tokens(function_definitions)
        return SPECIAL_TOKEN_INSTRUCTION_TEMPLATE.format(tools_list=tools_list)
    elif state.settings.enable_xml:
        standard_functions = "\n".join([bash_xml, python_xml, set_timeout_xml])
        intermediate_scoring = state.settings.intermediate_scoring
        if intermediate_scoring:
            standard_functions += "\n".join([score_xml, score_log_xml])
        else:
            standard_functions += "\n".join([submit_xml])
        return standard_functions
    else:  # use backticks function
        standard_functions = "\n".join(
            [bash_backticks, python_backticks, set_timeout_backticks]
        )
        intermediate_scoring = state.settings.intermediate_scoring
        if intermediate_scoring:
            standard_functions += "\n".join([score_backticks, score_log_backticks])
        else:
            standard_functions += f"\n{submit_backticks}"
        return standard_functions


def parse_completion_function_names(
    state: Union[triframeState, ModularState], completion: str
) -> List[Dict[str, Any]]:
    if state.settings.enable_special_tokens:
        function_names = re.findall(r"<｜tool▁sep｜>(\w+)", completion)
    elif state.settings.enable_xml:
        function_names = re.findall(r"<(\w+)>", completion)
    else:
        function_names = re.findall(r"```(\w+)", completion)
    return function_names


# def parse_first_backticks_function_call(
#     function_name: str,
#     completion: str,
# ) -> Dict[str, Any] | None:
#     # get the last occurrence of the function name
#     pattern = rf"```{function_name}(.*?)```"
#     matches = re.findall(pattern, completion, re.DOTALL)
#     if not matches:
#         return None
#     function_args = matches[0].strip()
#     return function_args


# def parse_first_xml_function_call(
#     function_name: str, completion: str
# ) -> Dict[str, Any] | None:
#     # get the last occurrence of the function name
#     pattern = rf"<{function_name}>(.*?)</{function_name}>"
#     matches = re.findall(pattern, completion, re.DOTALL)
#     if not matches:
#         return None
#     function_args = matches[0].strip()
#     return function_args


def parse_first_backticks_function_call(
    function_names: List[str], completion: str
) -> Dict[str, Any] | None:
    """
    Finds the first occurrence of a fenced code block with one of the given
    function names, and returns a dictionary of the form:
      {
        "name": <the function name>,
        "arguments": <the content inside the code block>
      }
    """
    if function_names == ["advise"]:
        # Special handling for advise to avoid nested backticks issues
        # Find the ```advise block and match until the first ``` that isn't part of a nested block
        start_pattern = r"```advise\s*"
        start_match = re.search(start_pattern, completion)
        if not start_match:
            return None
        
        start_pos = start_match.end()
        content = completion[start_pos:]
        
        # Find the closing ``` that isn't immediately preceded by json or other code block indicators
        lines = content.split('\n')
        result_lines = []
        in_nested_block = False
        
        for line in lines:
            if line.strip() == '```':
                if in_nested_block:
                    # This closes a nested block
                    in_nested_block = False
                    result_lines.append(line)
                else:
                    # This closes the advise block
                    break
            elif line.strip().startswith('```'):
                # This starts a nested block
                in_nested_block = True
                result_lines.append(line)
            else:
                result_lines.append(line)
        
        function_args = '\n'.join(result_lines).strip()
        return {"name": "advise", "arguments": function_args}
    else:
        pattern = (
            r"```(" + "|".join(re.escape(fn) for fn in function_names) + r")\s*(.*?)```"
        )
        match = re.search(pattern, completion, flags=re.DOTALL)
        if not match:
            return None

        function_name = match.group(1).strip()
        function_args = match.group(2).strip()
        return {"name": function_name, "arguments": function_args}


def parse_first_xml_function_call(
    function_names: List[str], completion: str
) -> Dict[str, Any] | None:
    pattern = r"<(" + "|".join(re.escape(fn) for fn in function_names) + r")>(.*?)</"
    match = re.search(pattern, completion, flags=re.DOTALL)
    if not match:
        return None

    function_name = match.group(1).strip()
    function_args = match.group(2).strip()
    return {"name": function_name, "arguments": function_args}


def parse_first_special_token_function_call(
    function_names: List[str], completion: str
) -> Dict[str, Any] | None:
    """
    Parse special token format function calls like:
    <｜tool▁calls▁begin｜><｜tool▁call▁begin｜>function<｜tool▁sep｜>FUNCTION_NAME
    ```json
    {"param": "value"}
    ```<｜tool▁call▁end｜><｜tool▁calls▁end｜>
    """
    # Pattern to match the special token format
    pattern = r"<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>function<｜tool▁sep｜>(" + \
              "|".join(re.escape(fn) for fn in function_names) + \
              r")\s*```json\s*(.*?)\s*```<｜tool▁call▁end｜><｜tool▁calls▁end｜>"
    
    match = re.search(pattern, completion, flags=re.DOTALL)
    if not match:
        return None
    
    function_name = match.group(1).strip()
    json_args = match.group(2).strip()
    
    return {"name": function_name, "arguments": json_args}


def find_completion_until_function_call(
    enable_xml: bool,
    function_name: str,
    completion: str,
    enable_special_tokens: bool = False,
) -> str:
    if enable_special_tokens:
        start_pos = completion.find("<｜tool▁calls▁begin｜>")
    elif enable_xml:
        start_pos = completion.find(f"</{function_name}>")
    else:
        # Find the end of the code block
        start_pos = completion.find(f"```{function_name}")

    return completion[:start_pos] if start_pos != -1 else completion


def parse_completions_function_call(
    enable_xml: bool,
    function_names: List[str],
    completion: str,
    func_name_to_args: Dict[str, Tuple[str, type]] = STANDARD_FUNCTION_VALIDATIONS,
    enable_special_tokens: bool = False,
) -> Dict[str, Any] | None:
    if enable_special_tokens:
        parsed_function = parse_first_special_token_function_call(function_names, completion)
    elif enable_xml:
        parsed_function = parse_first_xml_function_call(function_names, completion)
    else:
        parsed_function = parse_first_backticks_function_call(
            function_names, completion
        )

    if parsed_function is None:
        return None, completion

    function_name = parsed_function["name"]
    args = parsed_function["arguments"]

    completion_until_function_call = find_completion_until_function_call(
        enable_xml, function_name, completion, enable_special_tokens
    )

    # if function doesn't need args, return the function name and empty args
    if not func_name_to_args[function_name]:
        return {
            "name": function_name,
            "arguments": json.dumps({}),
        }, completion_until_function_call

    # For special token format, args should already be JSON
    if enable_special_tokens:
        try:
            # Validate JSON is parseable
            json.loads(args)
            return {
                "name": function_name,
                "arguments": args,
            }, completion_until_function_call
        except json.JSONDecodeError:
            return None, completion_until_function_call
    
    # For other formats, convert to JSON
    arg_name, arg_type = func_name_to_args[function_name]
    if arg_type is not None and not args:
        return None, completion_until_function_call
    try:
        parsed_function = {arg_name: arg_type(args)}
        return {
            "name": function_name,
            "arguments": json.dumps(parsed_function),
        }, completion_until_function_call
    except ValueError:
        return None, completion_until_function_call


def parse_backticks_json(completion: str) -> Dict[str, Any] | None:
    if "```json" not in completion:
        return None
    json_str = completion.split("```json")[1].split("```")[0]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


# def remove_backticks_code_blocks(function_call: Dict[str, Any], text: str) -> str:
#     pattern = r"```[^`]*```"
#     cleaned_text = re.sub(pattern, "", text)
#     cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
#     return cleaned_text.strip()


# def remove_xml_code_blocks(function_call: Dict[str, Any], text: str) -> str:
#     # only remove the code blocks with the function name
#     # FIXME: not tested
#     pattern = (
#         rf"<(?!{function_call['name']}\b)[^>]+>.*?</(?!{function_call['name']}\b)[^>]+>"
#     )
#     cleaned_text = re.sub(pattern, "", text, flags=re.DOTALL)
#     cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
#     return cleaned_text.strip()


# def remove_code_blocks(
#     state: Union[triframeState, ModularState], function_call: Dict[str, Any], text: str
# ) -> str:
#     if state.settings.enable_xml:
#         return remove_xml_code_blocks(function_call, text)
#     else:
#         return remove_backticks_code_blocks(function_call, text)


def combine_function_call_and_content(
    state: Union[triframeState, ModularState],
    function_call: Dict[str, Any],
    content: str,
) -> str:
    if not function_call:
        return content
    if "arguments" not in function_call:
        raise ValueError(f"Function call has no arguments: {function_call}")
    
    if not json.loads(function_call["arguments"]):
        if state.settings.enable_special_tokens:
            function_call_str = f"""<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>function<｜tool▁sep｜>{function_call['name']}
```json
{{}}
```<｜tool▁call▁end｜><｜tool▁calls▁end｜>"""
        elif state.settings.enable_xml:
            function_call_str = f"<{function_call['name']}></{function_call['name']}>"
        else:
            function_call_str = f"```{function_call['name']}\n```"
    else:
        if state.settings.enable_special_tokens:
            function_call_str = f"""<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>function<｜tool▁sep｜>{function_call['name']}
```json
{function_call['arguments']}
```<｜tool▁call▁end｜><｜tool▁calls▁end｜>"""
        elif state.settings.enable_xml:
            args = list(json.loads(function_call["arguments"]).values())[0]
            function_call_str = (
                f"<{function_call['name']}>\n{args}\n</{function_call['name']}>"
            )
        else:
            args = list(json.loads(function_call["arguments"]).values())[0]
            function_call_str = f"```{function_call['name']}\n{args}\n```"
    return f"{content}\n\nFinal Executed Function:\n{function_call_str}"


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
    elif tool_name == "bash":
        return BashRequest(
            type="bash",
            params=BashParams(command=tool_args["command"]),
            metadata=metadata,
        )
    elif tool_name == "python":
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


def get_completions_without_cot(completion: str) -> str:
    """
    Remove the CoT between <think> and the last </think> tags from the completion.
    """
    # If CoT has no </think> tags, return the whole completion without the <think> tags
    if "</think>" not in completion and "<think>" in completion:
        return completion.replace("<think>", "")
    return re.sub(r"<think>.*</think>", "", completion, flags=re.DOTALL).strip()
