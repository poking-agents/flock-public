from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str | List[Dict[str, Any]]
    name: Optional[str] = None
    function_call: Optional[Dict] = None


class Option(BaseModel):
    content: str
    function_call: Optional[Dict] = None
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional metadata about the option's source"
    )
    extra_outputs: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional extra outputs"
    )


class Node(BaseModel):
    source: str
    options: List[Option]
    token_usage: Optional[int] = None
    actions_usage: Optional[int] = None
    time_usage: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional metadata about the node"
    )

    def model_dump(self, *args, **kwargs):
        """Custom serialization for Pydantic v2"""
        d = super().model_dump(*args, **kwargs)
        d["options"] = [opt.model_dump() for opt in self.options]
        return d
