"""State type definitions for workflows"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from type_defs.base import Node, Option
from type_defs.operations import MiddlemanSettings, OperationResult


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
    enable_subagents: bool = Field(False, description="Enable subagent launching")


class triframeState(AgentState):
    settings: triframeSettings = Field(default_factory=triframeSettings)
    active_subagents: List[Dict[str, Any]] = Field(default_factory=list)
    subagent_config: Optional[Dict[str, Any]] = Field(default=None)
    status: str = Field("initialized", description="State status (for subagents)")

    def is_subagent(self) -> bool:
        """Check if this state represents a subagent"""
        return self.subagent_config is not None

    def add_subagent(
        self, agent_id: str, task: str, approach: str, include_task_description: bool
    ) -> None:
        """Add a subagent to active agents"""
        self.active_subagents.append(
            {
                "id": agent_id,
                "task": task,
                "approach": approach,
                "include_task_description": include_task_description,
                "status": "initialized",
            }
        )

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
