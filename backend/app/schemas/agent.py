from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentTestRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_history: list[dict[str, str]] | None = None
    customer_context: dict[str, Any] | None = None


class AgentTestResponse(BaseModel):
    response: str
    model: str
    status: str = "ok"


class GeminiHealthResponse(BaseModel):
    status: str
    configured: bool
    model: str | None = None
