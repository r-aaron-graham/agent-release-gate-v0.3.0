from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings

Role = Literal["viewer", "analyst", "architect", "admin"]
Sensitivity = Literal["low", "medium", "high"]
Outcome = Literal["approved", "clarify", "fallback", "review_required", "refused"]
ReviewStatus = Literal["open", "approved", "rejected"]


class DecisionInput(BaseModel):
    user_name: str = Field(min_length=1, max_length=100)
    role: Role
    prompt: str = Field(min_length=3, max_length=settings.max_prompt_length)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    sensitivity: Sensitivity
    requested_action: str | None = Field(default=None, max_length=100)

    @field_validator("user_name", "prompt", "requested_action", mode="before")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class DecisionOutput(BaseModel):
    request_id: int
    outcome: Outcome
    risk_score: int
    reasons: list[str]
    suggested_response: str
    created_at: datetime


class ReviewResolution(BaseModel):
    reviewer: str = Field(min_length=1, max_length=100)
    decision: Literal["approved", "rejected"]
    resolution_note: str = Field(min_length=3, max_length=1000)

    @field_validator("reviewer", "resolution_note", mode="before")
    @classmethod
    def strip_strings(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class RequestListItem(BaseModel):
    id: int
    user_name: str
    role: Role
    prompt: str
    prompt_preview: str
    evidence_strength: float
    sensitivity: Sensitivity
    requested_action: str | None = None
    outcome: Outcome
    risk_score: int
    reason_summary: str
    suggested_response: str
    created_at: datetime
    review_id: int | None = None
    review_status: ReviewStatus | None = None
    review_reviewer: str | None = None


class PaginatedRequestList(BaseModel):
    items: list[RequestListItem]
    pagination: PaginationMeta


class ReviewResolutionOutput(BaseModel):
    review_id: int
    status: Literal["approved", "rejected"]
    reviewer: str
    resolution_note: str


class AdminLoginInput(BaseModel):
    api_key: str = Field(min_length=1, max_length=200)


class ErrorContext(BaseModel):
    message: str
    prompt: str | None = None
