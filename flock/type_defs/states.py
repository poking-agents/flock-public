"""State type definitions for workflows"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from flock.type_defs.base import Message, Node, Option
from flock.type_defs.operations import MiddlemanSettings, OperationResult


class BaseState(BaseModel):
    id: str = Field("", description="State ID, used as a filename")
    pass


DEFAULT_TIMEOUT = 60


class AgentState(BaseState):
    previous_results: List[List[OperationResult]] = Field(default_factory=list)
    task_string: str = Field("", description="Task description")
    nodes: List[Node] = Field(default_factory=list)
    timeout: int = Field(DEFAULT_TIMEOUT, description="Command timeout in seconds")
    token_limit: int = Field(300000, description="Maximum tokens allowed")
    token_usage: int = Field(0, description="Current token usage")
    time_limit: float = Field(604800.0, description="Maximum time allowed in seconds")
    time_usage: float = Field(0.0, description="Current time usage in seconds")
    actions_limit: int = Field(1000, description="Maximum actions allowed")
    actions_usage: int = Field(0, description="Current actions usage")
    scoring: Dict[str, Any] = Field(
        default_factory=dict, description="Task scoring configuration"
    )
    output_limit: int = Field(
        10000, description="Maximum output length included in agent requests"
    )
    context_trimming_threshold: int = Field(
        500000, description="Character threshold for context trimming"
    )
    last_rating_options: Optional[List[Option]] = None

    def update_usage(self):
        latest_results = self.previous_results[-1]
        usage_result = next((r for r in latest_results if r.type == "get_usage"), None)
        if usage_result:
            usage = usage_result.result.usage
            self.token_usage = usage.tokens
            self.actions_usage = usage.actions
            self.time_usage = usage.total_seconds
            if self.nodes:
                self.nodes[-1].token_usage = usage.tokens
                self.nodes[-1].actions_usage = usage.actions
                self.nodes[-1].time_usage = usage.total_seconds
        elif self.nodes:
            self.nodes[-1].token_usage = self.token_usage
            self.nodes[-1].actions_usage = self.actions_usage
            self.nodes[-1].time_usage = self.time_usage


class triframeSettings(BaseModel):
    advisors: List[MiddlemanSettings] = Field(
        default_factory=lambda: [MiddlemanSettings()],
        description="List of advisor model settings",
    )
    actors: List[MiddlemanSettings] = Field(
        default_factory=lambda: [MiddlemanSettings()],
        description="List of actor model settings",
    )
    raters: List[MiddlemanSettings] = Field(
        default_factory=lambda: [MiddlemanSettings()],
        description="List of rater model settings",
    )
    limit_type: str = Field("token", description="Type of usage limit")
    intermediate_scoring: bool = Field(False, description="Enable intermediate scoring")
    require_function_call: bool = Field(False, description="Require function calls")
    enable_advising: bool = Field(True, description="Enable advisor phase")
    enable_tool_use: bool = Field(True, description="Enable tool use")
    enable_xml: bool = Field(
        False, description="Enable XML mode when enable_tool_use is False"
    )


class triframeState(AgentState):
    settings: triframeSettings = Field(default_factory=triframeSettings)


class ModularSettings(BaseModel):
    generator: MiddlemanSettings = Field(default_factory=MiddlemanSettings)
    limit_type: str = Field("token", description="Type of usage limit")
    intermediate_scoring: bool = Field(False, description="Enable intermediate scoring")
    enable_tool_use: bool = Field(True, description="Enable tool use")
    enable_xml: bool = Field(
        False, description="Enable XML mode when enable_tool_use is False"
    )


class ModularState(AgentState):
    settings: ModularSettings = Field(default_factory=ModularSettings)
    messages: List[Message] = Field(default_factory=list)
