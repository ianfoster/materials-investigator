from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime
import uuid

StepType = Literal["HYPOTHESIS","DESIGN","EXECUTE","INTERPRET","UPDATE"]

class Hypothesis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    statement: str
    candidates: List[str]
    assumptions: List[str] = []

class TestDesign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hypothesis_id: str
    target_property: str
    candidates: List[str]
    rationale: str

class ToolCall(BaseModel):
    tool: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    ok: bool
    error: Optional[str] = None

class Interpretation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hypothesis_id: str
    updated_beliefs: Dict[str, float]

class Budget(BaseModel):
    max_tool_calls: int
    tool_calls_used: int = 0

class Event(BaseModel):
    run_id: str
    step: StepType
    payload: Dict[str, Any]
    ts: datetime = Field(default_factory=datetime.utcnow)
