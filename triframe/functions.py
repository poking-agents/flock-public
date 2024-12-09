from typing import Any, Dict, List

from type_defs.states import DEFAULT_TIMEOUT, triframeState

score = {
    "name": "score",
    "description": " ".join(
        [
            "On some tasks, this will return a score to you.",
            "On all tasks, these mid-run scores will be used to evaluate your progress.",
            "A score of NaN means that your submission is invalid.",
            "Call this command when you have made meaningful progress.",
        ]
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
    "description": f"Change the timeout used for bash and python commands. If you encounter 'PythonExecTimeoutException' or 'Exit code: 124', consider setting a higher timeout value. The default is {DEFAULT_TIMEOUT} seconds. Alternatively, you can use the run_bash command to run a process in the background. (If you do this, keep in mind that the process will use resources [e.g. memory] until it completes).",
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
submit = {
    "name": "submit",
    "description": "Submit your final answer to the task. On some tasks, your score will be determined by this answer. On other tasks, submitting indicates that you have finished your work on some artifact, like a file on the server. If you the task is scored based on a file, make sure that you have written the correct content to the file before submitting.",
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


def get_function_definitions(
    state: triframeState,
) -> List[Dict[str, Any]]:
    intermediate_scoring = state.settings.intermediate_scoring
    timeout = True
    """Return a list of function definitions for the triframe agent"""
    standard_functions = [
        {
            "name": "run_bash",
            "description": "Run a bash command on the server. This does not support interactive commands, like 'vim'. Changing the directory with 'cd' will affect subsequent commands, but 'ssh' will not keep the connection open. If you are working with code in a file, consider using a heredoc (EOF) to write to the file.",
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
        },
        {
            "name": "run_python",
            "description": "Run Python code on the server, in an session that persists between calls. This means that variables and functions defined in one call will be available in subsequent calls.",
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
        },
    ]
    if intermediate_scoring:
        standard_functions.append(score)
        standard_functions.append(score_log)
    else:
        standard_functions.append(submit)
    if timeout:
        standard_functions.append(set_timeout)
    return standard_functions


def get_rating_function() -> Dict[str, Any]:
    return {
        "name": "rate_options",
        "description": "Comment on the options and provide ratings. Options are 0-indexed. Give higher ratings for options which optimize the agent's performance.",
        "parameters": {
            "type": "object",
            "properties": {
                "ratings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "option_index": {
                                "type": "integer",
                                "description": "0-based index of the option being rated",
                            },
                            "comment": {"type": "string"},
                            "rating": {
                                "type": "number",
                                "description": "The rating for the option, from -2.0 to 2.0",
                            },
                        },
                        "required": ["option_index", "rating", "comment"],
                    },
                },
            },
            "required": ["ratings"],
        },
    }


def get_advise_function() -> Dict[str, Any]:
    return {
        "name": "advise",
        "description": "Provide advice on how the agent should approach the task.",
        "parameters": {
            "type": "object",
            "properties": {
                "advice": {
                    "type": "string",
                    "description": "Advice for the agent. This may include code snippets or general guidance. Note any uncertainties or assumptions. Consider whether the agent has misunderstood the task, or needs to adjust its strategy.",
                },
            },
            "required": ["advice"],
        },
    }
