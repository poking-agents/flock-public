"""Utility functions for operation and phase handling"""

from flock.utils.phase_utils import (
    get_last_completion,
    get_last_result,
    run_phase,
)
from flock.utils.state import (
    load_state,
    save_state,
)

__all__ = [
    "run_phase",
    # Operation result utilities
    "extract_result",
    "is_error_result",
    "get_error_message",
    # Phase result utilities
    "get_last_result",
    "get_last_completion",
    # State management utilities
    "load_state",
    "save_state",
]
