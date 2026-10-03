from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StartCallRequest(BaseModel):
    customer_id: int = Field(..., gt=0)


class StartCallResponse(BaseModel):
    call_id: int
    customer: dict[str, Any]
    strategy: dict[str, Any]


class CallMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class CallMessageResponse(BaseModel):
    call_id: int
    response: str
    turn_number: int
    tool_calls: list[dict[str, Any]] = []


class EndCallRequest(BaseModel):
    summary: str | None = None


class EndCallResponse(BaseModel):
    call_id: int
    status: str
    outcome: dict[str, Any]
    metrics: dict[str, Any]
