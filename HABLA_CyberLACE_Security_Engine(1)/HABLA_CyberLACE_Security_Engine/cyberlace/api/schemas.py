from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class PromptGuardRequest(BaseModel):
    agent_id: str
    user_id: str = "anonymous"
    prompt: str
    context: Dict[str, Any] = Field(default_factory=dict)
    session_id: str = "default"


class MemoryGuardRequest(BaseModel):
    agent_id: str
    user_id: str = "anonymous"
    memory_text: str
    task_context: Dict[str, Any] = Field(default_factory=dict)
    session_id: str = "default"


class ToolGuardRequest(BaseModel):
    agent_id: str
    user_id: str = "anonymous"
    tool_name: str
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    task_context: Dict[str, Any] = Field(default_factory=dict)
    session_id: str = "default"


class OutputGuardRequest(BaseModel):
    agent_id: str
    user_id: str = "anonymous"
    output: str
    context: Dict[str, Any] = Field(default_factory=dict)
    session_id: str = "default"


class ExternalActionRequest(BaseModel):
    agent_id: str
    user_id: str = "anonymous"
    action_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    session_id: str = "default"


class GenericEventRequest(BaseModel):
    event: Dict[str, Any]
