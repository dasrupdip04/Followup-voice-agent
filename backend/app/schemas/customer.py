from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CustomerBase(BaseModel):
    id: int
    customer_number: str
    full_name: str
    phone_number: str
    email: str
    date_of_birth: date
    city: str
    bank_name: str
    preferred_language: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerRead(CustomerBase):
    pass


class CustomerListResponse(BaseModel):
    items: list[CustomerRead]
    total: int
    limit: int
    offset: int


class LoanRead(BaseModel):
    id: int
    customer_id: int
    loan_number: str
    loan_type: str
    principal_amount: Decimal
    outstanding_amount: Decimal
    interest_rate: Decimal
    emi_amount: Decimal
    due_date: date
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentRead(BaseModel):
    id: int
    loan_id: int
    amount: Decimal
    payment_date: datetime
    payment_method: str
    status: str
    transaction_reference: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CallOutcomeRead(BaseModel):
    id: int
    call_id: int
    outcome_type: str
    promised_amount: Decimal | None = None
    promised_date: date | None = None
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CallMetricRead(BaseModel):
    id: int
    call_id: int
    total_turns: int
    user_turns: int
    agent_turns: int
    avg_response_latency_ms: Decimal | None = None
    avg_stt_latency_ms: Decimal | None = None
    avg_llm_latency_ms: Decimal | None = None
    avg_tts_latency_ms: Decimal | None = None
    user_interruptions: int
    agent_interruptions: int
    tool_calls: int
    tool_failures: int
    tokens_input: int
    tokens_output: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PreviousCallRead(BaseModel):
    id: int
    customer_id: int
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    status: str
    agent_id: str
    created_at: datetime
    outcome: CallOutcomeRead | None = None
    metric: CallMetricRead | None = None

    model_config = ConfigDict(from_attributes=True)


class CustomerContextResponse(BaseModel):
    customer: CustomerRead
    loans: list[LoanRead]
    payments: list[PaymentRead]
    previous_calls: list[PreviousCallRead]

