from typing import Any, Dict


def get_rating_function() -> Dict[str, Any]:
    return {
        "name": "rate_options",
        "description": (
            "Comment on the options and provide ratings. Options are 0-indexed. "
            "Give higher ratings for options which optimize the agent's performance."
        ),
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
                                "description": (
                                    "0-based index of the option being rated"
                                ),
                            },
                            "comment": {"type": "string"},
                            "rating": {
                                "type": "number",
                                "description": (
                                    "The rating for the option, from -2.0 to 2.0"
                                ),
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
                    "description": (
                        "Advice for the agent. This may include code snippets or "
                        "general guidance. Note any uncertainties or assumptions. "
                        "Consider whether the agent has misunderstood the task, "
                        "or needs to adjust its strategy."
                    ),
                },
            },
            "required": ["advice"],
        },
    }
