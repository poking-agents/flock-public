from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel
from typing_extensions import TypedDict

from flock.type_defs.operations import BaseOperationRequest, BaseOperationResult
from flock.type_defs.states import AgentState


class PreviousOperations(BaseModel):
    updates: List[Tuple[BaseOperationRequest, BaseOperationResult]] = []
    error: Optional[str] = None
    status: str = "success"


class StateRequest(BaseModel):
    state: Union[
        AgentState,
        Dict[str, Any],
    ]
    state_model: str
    operations: List[BaseOperationRequest]
    next_phase: Optional[str] = None
    delay: Optional[int] = None


class WorkflowData(TypedDict):
    state_id: str
    operations: Dict[str, Any]
    current_phase: Optional[str]
    next_phase: Optional[str]
    delay: Optional[int]
