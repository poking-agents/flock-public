from typing import Any, Dict, List

from type_defs.states import DEFAULT_TIMEOUT, triframeState

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

score_log = {
    "name": "score_log",
    "description": "Get the history of your scores.",
    "parameters": {},
}

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


def get_function_definitions(
    state: triframeState,
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
