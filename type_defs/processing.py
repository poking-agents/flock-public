"""Processing mode definitions"""

from enum import Enum


class ProcessingMode(str, Enum):
    HOOKS = "hooks"
    MIDDLEMAN_SIMULATED = "middleman_simulated"
