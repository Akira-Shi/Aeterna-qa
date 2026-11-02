"""Pydantic request/response schemas."""
from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

TaskType = Literal["binary", "multiclass", "regression"]
ModelFamily = Literal["linear", "tree_ensemble", "distance", "neural"]


class Stage1Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: str
    target: str = Field(min_length=1)
    task_type: TaskType = "binary"
    positive_label: Optional[Union[str, int, float]] = None
    model_family: ModelFamily = "linear"
    id_columns: list[str] = []
    drop_columns: list[str] = []
    planner: Literal["rule", "groq"] = "rule"


class RerunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    planner: Literal["rule"] = "rule"


class StepDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step: int = Field(ge=0)
    action: Literal["accept", "edit"]
    method: Optional[str] = None


class ApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[StepDecision] = []     # steps not listed are accepted as the rule proposed them
