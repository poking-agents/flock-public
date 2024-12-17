"""Operation request and result type definitions"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict
from pyhooks.types import MiddlemanModelOutput, MiddlemanSettings, ScoreLogEntry

ParamsT = TypeVar("ParamsT", bound=BaseModel)
ResultT = TypeVar("ResultT", bound=BaseModel)


class OperationMetadata(BaseModel):
    purpose: Optional[str] = None
    phase: Optional[str] = None
    state_id: Optional[str] = None
    tournament_id: Optional[str] = None
    round_number: Optional[int] = None
    match_index: Optional[int] = None
    agent_ids: Optional[List[str]] = None
    model_config = ConfigDict(extra="allow")


class BaseOperationRequest(BaseModel, Generic[ParamsT]):
    type: str
    params: ParamsT
    metadata: Optional[OperationMetadata] = None


class BaseOperationResult(BaseModel, Generic[ResultT]):
    type: str
    result: ResultT
    error: Optional[str] = None
    metadata: Optional[OperationMetadata] = None


class InitWorkflowParams(BaseModel):
    workflow_type: str


class InitWorkflowOutput(BaseModel):
    state_id: str
    settings_path: str


class InitWorkflowRequest(BaseOperationRequest[InitWorkflowParams]):
    type: Literal["init_workflow"]
    params: InitWorkflowParams


class InitWorkflowResult(BaseOperationResult[InitWorkflowOutput]):
    type: Literal["init_workflow"]
    result: InitWorkflowOutput


class ScoreParams(BaseModel):
    pass


class ScoreRequest(BaseOperationRequest[ScoreParams]):
    type: Literal["score"]
    params: ScoreParams


class ExecResult(BaseModel):
    exitStatus: int
    stdout: str
    stderr: str


class ScoreOutput(BaseModel):
    message: Dict[str, Any]


class ScoreResult(BaseOperationResult[ScoreOutput]):
    type: Literal["score"]
    result: ScoreOutput


class ScoreLogParams(BaseModel):
    pass


class ScoreLogRequest(BaseOperationRequest[ScoreLogParams]):
    type: Literal["score_log"]
    params: ScoreLogParams


class ScoreLogResult(BaseOperationResult[List[ScoreLogEntry]]):
    type: Literal["score_log"]
    result: List[ScoreLogEntry]


class BashOutput(BaseModel):
    stdout: str
    stderr: str
    status: Optional[int] = None


class BashParams(BaseModel):
    command: str
    timeout: Optional[int] = None
    agent_id: Optional[str] = None
    model_config = ConfigDict(extra="allow")

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Custom serialization for Pydantic v2"""
        data = super().model_dump(*args, **kwargs)
        return {k: v for k, v in data.items() if v is not None}


class BashRequest(BaseOperationRequest[BashParams]):
    type: Literal["bash"]
    params: BashParams


class BashResult(BaseOperationResult[BashOutput]):
    type: Literal["bash"]
    result: BashOutput


class PythonParams(BaseModel):
    code: str
    timeout: Optional[int] = None


class PythonOutput(BaseModel):
    output: str
    error: Optional[str] = None


class PythonRequest(BaseOperationRequest[PythonParams]):
    type: Literal["python"]
    params: PythonParams


class PythonResult(BaseOperationResult[PythonOutput]):
    type: Literal["python"]
    result: PythonOutput


class GenerationSettings(BaseModel):
    model: str
    temp: float = 0.0
    n: int = 1
    max_tokens: Optional[int] = None
    stop: List[str] = []
    logprobs: Optional[int] = None
    logit_bias: Optional[Dict[str, float]] = None
    function_call: Optional[Dict[str, Any]] = None
    cache_key: Optional[str] = None
    delegation_token: Optional[str] = None


class GenerationParams(BaseModel):
    settings: MiddlemanSettings
    template: Optional[str] = None
    templateValues: Optional[Dict[str, Any]] = None
    messages: Optional[List[Dict[str, Any]]] = None
    functions: Optional[Any] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    extraParameters: Optional[Dict[str, Any]] = None


class GenerationOutput(BaseModel):
    error: Any = None
    non_blocking_errors: Optional[List[str]] = None
    outputs: Optional[List[MiddlemanModelOutput]] = None
    n_completion_tokens_spent: Optional[int] = None
    n_prompt_tokens_spent: Optional[int] = None
    cost: Optional[float] = None
    duration_ms: Optional[int] = None


class GenerationRequest(BaseOperationRequest[GenerationParams]):
    type: Literal["generate"]
    params: GenerationParams


class GenerationResult(BaseOperationResult[GenerationOutput]):
    type: Literal["generate"]
    result: GenerationOutput


class SubmissionParams(BaseModel):
    submission: str
    format: Optional[str] = None


class SubmissionOutput(BaseModel):
    status: str
    message: str
    submission_id: Optional[str] = None


class SubmissionRequest(BaseOperationRequest[SubmissionParams]):
    type: Literal["submit"]
    params: SubmissionParams


class SubmissionResult(BaseOperationResult[SubmissionOutput]):
    type: Literal["submit"]
    result: SubmissionOutput


class LogParams(BaseModel):
    content: Any
    level: str = "INFO"


class LogOutput(BaseModel):
    status: str
    message: str
    timestamp: str


class LogRequest(BaseOperationRequest[LogParams]):
    type: Literal["log"]
    params: LogParams


class LogResult(BaseOperationResult[LogOutput]):
    type: Literal["log"]
    result: LogOutput


class LogWithAttributesParams(BaseModel):
    content: Any
    attributes: Dict[str, Any]
    timestamp: Optional[datetime] = None


class LogWithAttributesOutput(BaseModel):
    status: str
    message: str
    timestamp: str
    attributes: Dict[str, Any]


class LogWithAttributesRequest(BaseOperationRequest[LogWithAttributesParams]):
    type: Literal["log_with_attributes"]
    params: LogWithAttributesParams


class LogWithAttributesResult(BaseOperationResult[LogWithAttributesOutput]):
    type: Literal["log_with_attributes"]
    result: LogWithAttributesOutput


class ActionParams(BaseModel):
    action_type: str
    parameters: Dict[str, Any]
    timestamp: Optional[datetime] = None


class ActionOutput(BaseModel):
    status: str
    message: str
    action: Dict[str, Any]


class ActionRequest(BaseOperationRequest[ActionParams]):
    type: Literal["action"]
    params: ActionParams


class ActionResult(BaseOperationResult[ActionOutput]):
    type: Literal["action"]
    result: ActionOutput


class ObservationParams(BaseModel):
    observation_type: str
    content: Any
    timestamp: Optional[datetime] = None


class ObservationOutput(BaseModel):
    status: str
    message: str
    observation: Dict[str, Any]


class ObservationRequest(BaseOperationRequest[ObservationParams]):
    type: Literal["observation"]
    params: ObservationParams


class ObservationResult(BaseOperationResult[ObservationOutput]):
    type: Literal["observation"]
    result: ObservationOutput


class GetUsageParams(BaseModel):
    pass


class RunUsage(BaseModel):
    tokens: int
    actions: int
    total_seconds: int
    cost: float


class UsageCheckpoint(BaseModel):
    tokens: Optional[int] = None
    actions: Optional[int] = None
    total_seconds: Optional[int] = None
    cost: Optional[float] = None


class GetUsageOutput(BaseModel):
    checkpoint: Optional[UsageCheckpoint] = None
    isPaused: bool
    usage: RunUsage
    usageLimits: RunUsage


class GetUsageRequest(BaseOperationRequest[GetUsageParams]):
    type: Literal["get_usage"]
    params: GetUsageParams


class GetUsageResult(BaseOperationResult[GetUsageOutput]):
    type: Literal["get_usage"]
    result: GetUsageOutput


class GetTaskParams(BaseModel):
    pass


TaskPermissions = Literal["full_internet"]


class ScoringInfo(BaseModel):
    intermediate: bool
    visible_to_agent: bool
    score_on_usage_limits: bool


class GetTaskOutput(BaseModel):
    instructions: str
    permissions: List[TaskPermissions] = []
    scoring: ScoringInfo = ScoringInfo(
        intermediate=False, visible_to_agent=False, score_on_usage_limits=False
    )


class GetTaskRequest(BaseOperationRequest[GetTaskParams]):
    type: Literal["get_task"]
    params: GetTaskParams


class GetTaskResult(BaseOperationResult[GetTaskOutput]):
    type: Literal["get_task"]
    result: GetTaskOutput


class SaveStateParams(BaseModel):
    state_id: str
    state: Dict[str, Any]
    timestamp: str


class SaveStateOutput(BaseModel):
    status: str
    message: str
    snapshot_path: str


class SaveStateRequest(BaseOperationRequest[SaveStateParams]):
    type: Literal["save_state"]
    params: SaveStateParams


class SaveStateResult(BaseOperationResult[SaveStateOutput]):
    type: Literal["save_state"]
    result: SaveStateOutput


class WriteMessageParams(BaseModel):
    from_agent: str
    to_agent: str
    msg_type: str
    content: Dict[str, Any]


class WriteMessageOutput(BaseModel):
    status: str
    message: str
    timestamp: str


class WriteMessageRequest(BaseOperationRequest[WriteMessageParams]):
    type: Literal["write_message"]
    params: WriteMessageParams


class WriteMessageResult(BaseOperationResult[WriteMessageOutput]):
    type: Literal["write_message"]
    result: WriteMessageOutput


class ReadMessagesParams(BaseModel):
    agent_id: str
    remove: bool = True


class ReadMessagesOutput(BaseModel):
    messages: List[Dict[str, Any]]


class ReadMessagesRequest(BaseOperationRequest[ReadMessagesParams]):
    type: Literal["read_messages"]
    params: ReadMessagesParams


class ReadMessagesResult(BaseOperationResult[ReadMessagesOutput]):
    type: Literal["read_messages"]
    result: ReadMessagesOutput


REQUEST_MODELS = {
    "init_workflow": InitWorkflowRequest,
    "bash": BashRequest,
    "python": PythonRequest,
    "generate": GenerationRequest,
    "submit": SubmissionRequest,
    "get_task": GetTaskRequest,
    "get_usage": GetUsageRequest,
    "log": LogRequest,
    "log_with_attributes": LogWithAttributesRequest,
    "action": ActionRequest,
    "observation": ObservationRequest,
    "save_state": SaveStateRequest,
    "score": ScoreRequest,
    "score_log": ScoreLogRequest,
    "write_message": WriteMessageRequest,
    "read_messages": ReadMessagesRequest,
}
RESULT_MODELS = {
    "init_workflow": InitWorkflowResult,
    "bash": BashResult,
    "python": PythonResult,
    "generate": GenerationResult,
    "submit": SubmissionResult,
    "get_task": GetTaskResult,
    "get_usage": GetUsageResult,
    "log": LogResult,
    "log_with_attributes": LogWithAttributesResult,
    "action": ActionResult,
    "observation": ObservationResult,
    "save_state": SaveStateResult,
    "score": ScoreResult,
    "score_log": ScoreLogResult,
    "write_message": WriteMessageResult,
    "read_messages": ReadMessagesResult,
}
OperationRequest = Union[
    InitWorkflowRequest,
    BashRequest,
    PythonRequest,
    GenerationRequest,
    SubmissionRequest,
    LogRequest,
    LogWithAttributesRequest,
    ActionRequest,
    ObservationRequest,
    GetUsageRequest,
    GetTaskRequest,
    SaveStateRequest,
    ScoreRequest,
    ScoreLogRequest,
    WriteMessageRequest,
    ReadMessagesRequest,
]
OperationResult = Union[
    InitWorkflowResult,
    BashResult,
    PythonResult,
    GenerationResult,
    SubmissionResult,
    LogResult,
    LogWithAttributesResult,
    ActionResult,
    ObservationResult,
    GetUsageResult,
    GetTaskResult,
    SaveStateResult,
    ScoreResult,
    ScoreLogResult,
    ReadMessagesResult,
    WriteMessageResult,
]
