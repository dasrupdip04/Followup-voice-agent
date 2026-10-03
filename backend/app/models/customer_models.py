from typing import Any

from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, relationship

from app.db import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = Column(BigInteger, primary_key=True, index=True)
    customer_number: Mapped[str] = Column(String(20), nullable=False, unique=True)
    full_name: Mapped[str] = Column(String(200), nullable=False)
    phone_number: Mapped[str] = Column(String(30), nullable=False)
    email: Mapped[str] = Column(String(255), nullable=False, unique=True)
    date_of_birth: Mapped[date] = Column(Date, nullable=False)
    city: Mapped[str] = Column(String(100), nullable=False)
    bank_name: Mapped[str] = Column(String(150), nullable=False)
    preferred_language: Mapped[str] = Column(String(50), nullable=False)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    loans: Mapped[list["Loan"]] = relationship(back_populates="customer")
    calls: Mapped[list["Call"]] = relationship(back_populates="customer")


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = Column(BigInteger, primary_key=True, index=True)
    customer_id: Mapped[int] = Column(BigInteger, ForeignKey("customers.id"), nullable=False, index=True)
    loan_number: Mapped[str] = Column(String(40), nullable=False, unique=True)
    loan_type: Mapped[str] = Column(String(50), nullable=False)
    principal_amount: Mapped[float] = Column(Numeric(14, 2), nullable=False)
    outstanding_amount: Mapped[float] = Column(Numeric(14, 2), nullable=False)
    interest_rate: Mapped[float] = Column(Numeric(5, 2), nullable=False)
    emi_amount: Mapped[float] = Column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date] = Column(Date, nullable=False)
    status: Mapped[str] = Column(String(30), nullable=False)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    customer: Mapped[Customer] = relationship(back_populates="loans")
    payments: Mapped[list["Payment"]] = relationship(back_populates="loan")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = Column(BigInteger, primary_key=True, index=True)
    loan_id: Mapped[int] = Column(BigInteger, ForeignKey("loans.id"), nullable=False, index=True)
    amount: Mapped[float] = Column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    payment_method: Mapped[str] = Column(String(30), nullable=False)
    status: Mapped[str] = Column(String(30), nullable=False)
    transaction_reference: Mapped[str] = Column(String(80), nullable=False, unique=True)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    loan: Mapped[Loan] = relationship(back_populates="payments")


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[int] = Column(BigInteger, primary_key=True, index=True)
    customer_id: Mapped[int] = Column(BigInteger, ForeignKey("customers.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = Column(Integer, nullable=True)
    status: Mapped[str] = Column(String(30), nullable=False)
    agent_id: Mapped[str] = Column(String(80), nullable=False)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    customer: Mapped[Customer] = relationship(back_populates="calls")
    outcome: Mapped["CallOutcome"] = relationship(back_populates="call", uselist=False)
    metric: Mapped["CallMetric"] = relationship(back_populates="call", uselist=False)
    events: Mapped[list["CallEvent"]] = relationship(back_populates="call")
    conversation_turns: Mapped[list["ConversationTurn"]] = relationship(back_populates="call")


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id: Mapped[int] = Column(BigInteger, primary_key=True, index=True)
    call_id: Mapped[int] = Column(BigInteger, ForeignKey("calls.id"), nullable=False, index=True)
    speaker: Mapped[str] = Column(String(10), nullable=False)
    text: Mapped[str] = Column(Text, nullable=False)
    timestamp: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    latency_ms: Mapped[int | None] = Column(Integer, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    call: Mapped[Call] = relationship(back_populates="conversation_turns")


class CallEvent(Base):
    __tablename__ = "call_events"

    id: Mapped[int] = Column(BigInteger, primary_key=True, index=True)
    call_id: Mapped[int] = Column(BigInteger, ForeignKey("calls.id"), nullable=False, index=True)
    event_type: Mapped[str] = Column(String(60), nullable=False)
    timestamp: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    metadata_json: Mapped[dict[str, Any]] = Column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    call: Mapped[Call] = relationship(back_populates="events")


class CallOutcome(Base):
    __tablename__ = "call_outcomes"

    id: Mapped[int] = Column(BigInteger, primary_key=True, index=True)
    call_id: Mapped[int] = Column(BigInteger, ForeignKey("calls.id"), nullable=False, unique=True, index=True)
    outcome_type: Mapped[str] = Column(String(40), nullable=False)
    promised_amount: Mapped[float | None] = Column(Numeric(14, 2), nullable=True)
    promised_date: Mapped[date | None] = Column(Date, nullable=True)
    notes: Mapped[str | None] = Column(Text, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    call: Mapped[Call] = relationship(back_populates="outcome")


class CallMetric(Base):
    __tablename__ = "call_metrics"

    id: Mapped[int] = Column(BigInteger, primary_key=True, index=True)
    call_id: Mapped[int] = Column(BigInteger, ForeignKey("calls.id"), nullable=False, unique=True, index=True)
    total_turns: Mapped[int] = Column(Integer, nullable=False)
    user_turns: Mapped[int] = Column(Integer, nullable=False)
    agent_turns: Mapped[int] = Column(Integer, nullable=False)
    avg_response_latency_ms: Mapped[float | None] = Column(Numeric(10, 2), nullable=True)
    avg_stt_latency_ms: Mapped[float | None] = Column(Numeric(10, 2), nullable=True)
    avg_llm_latency_ms: Mapped[float | None] = Column(Numeric(10, 2), nullable=True)
    avg_tts_latency_ms: Mapped[float | None] = Column(Numeric(10, 2), nullable=True)
    user_interruptions: Mapped[int] = Column(Integer, nullable=False, default=0)
    agent_interruptions: Mapped[int] = Column(Integer, nullable=False, default=0)
    tool_calls: Mapped[int] = Column(Integer, nullable=False, default=0)
    tool_failures: Mapped[int] = Column(Integer, nullable=False, default=0)
    tokens_input: Mapped[int] = Column(Integer, nullable=False, default=0)
    tokens_output: Mapped[int] = Column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    call: Mapped[Call] = relationship(back_populates="metric")
