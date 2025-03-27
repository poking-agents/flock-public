"""Handler registry and exports"""

from typing import Dict

from handlers.action import handlers as action_handlers
from handlers.base import OperationHandler, get_handler
from handlers.bash import handlers as bash_handlers
from handlers.generate import handlers as generate_handlers
from handlers.log import (
    attributed_handlers as log_attributed_handlers,
)
from handlers.log import (
    handlers as log_handlers,
)
from handlers.observation import handlers as observation_handlers
from handlers.python import handlers as python_handlers
from handlers.save_state import handlers as save_state_handlers
from handlers.scoring import score_handlers, score_log_handlers
from handlers.submit import handlers as submit_handlers
from handlers.utility import (
    task_handlers,
    usage_handlers,
)
from type_defs import ProcessingMode

# Handler registry mapping operation types and modes to handler functions
handler_registry: Dict[str, Dict[ProcessingMode, OperationHandler]] = {
    "generate": generate_handlers,
    "bash": bash_handlers,
    "python": python_handlers,
    "submit": submit_handlers,
    "log": log_handlers,
    "log_with_attributes": log_attributed_handlers,
    "action": action_handlers,
    "observation": observation_handlers,
    "get_usage": usage_handlers,
    "get_task": task_handlers,
    "save_state": save_state_handlers,
    "score": score_handlers,
    "score_log": score_log_handlers,
}


def list_supported_operations() -> Dict[str, list[ProcessingMode]]:
    """Get a dictionary of supported operations and their available modes"""
    return {op_type: list(modes.keys()) for op_type, modes in handler_registry.items()}


__all__ = [
    "handler_registry",
    "list_supported_operations",
    "get_handler",
]
