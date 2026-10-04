"""Lightweight wrappers to reuse Phase 5/6 backend services from the LiveKit agent.

These wrappers avoid direct SQL access and instead call the existing service
classes in the backend. They keep Gemini and tool usage minimal and reuse
the server-side validation already implemented in the call lifecycle services.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import select
from app.services.call_lifecycle_service import CallLifecycleService
from app.db import SessionLocal
from app.models.customer_models import Call, CallEvent, ConversationTurn, Customer, Loan


def start_call_for_session(customer_id: int) -> Dict[str, Any]:
    """Start a Phase 6 call using existing lifecycle service and return call info.

    Returns the dict produced by `CallLifecycleService.start_call`.
    """
    session = SessionLocal()
    try:
        svc = CallLifecycleService(session)
        return svc.start_call(customer_id=customer_id)
    finally:
        session.close()


def end_call_for_session(call_id: int) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        svc = CallLifecycleService(session)
        return svc.end_call(call_id=call_id)
    finally:
        session.close()


def handle_message_for_session(call_id: int, message: str) -> Dict[str, Any]:
    """Route a transcript through the verified call lifecycle service."""
    session = SessionLocal()
    try:
        return CallLifecycleService(session).handle_message(call_id=call_id, message=message)
    finally:
        session.close()


def get_call_context_for_voice(call_id: int) -> Dict[str, Any]:
    """Load the existing call's customer, strategy, and target loan for voice UX."""
    session = SessionLocal()
    try:
        call = session.get(Call, call_id)
        if call is None:
            raise ValueError("Call not found")
        customer = session.get(Customer, call.customer_id)
        start_event = session.execute(
            select(CallEvent)
            .where(CallEvent.call_id == call_id, CallEvent.event_type == "CALL_STARTED")
            .order_by(CallEvent.id.asc())
        ).scalars().first()
        strategy = (start_event.metadata_json or {}).get("strategy", {}) if start_event else {}
        loans = session.execute(
            select(Loan)
            .where(Loan.customer_id == call.customer_id)
            .order_by(Loan.due_date.asc())
        ).scalars().all()
        main_loan = next((loan for loan in loans if loan.status.upper() == "OVERDUE"), None)
        if main_loan is None:
            main_loan = loans[0] if loans else None
        return {
            "call_id": call.id,
            "customer_id": call.customer_id,
            "customer_name": customer.full_name if customer else "Customer",
            "bank_name": customer.bank_name if customer else "the bank",
            "loan": {
                "loan_number": main_loan.loan_number,
                "loan_type": main_loan.loan_type,
                "outstanding_amount": str(main_loan.outstanding_amount),
            } if main_loan else None,
            "strategy": strategy,
        }
    finally:
        session.close()


def append_turn(call_id: int, role: str, text: str) -> None:
    """Persist a conversation turn directly to the `conversation_turns` table.

    This is a small helper used by the LiveKit runner to persist raw user or
    agent transcripts when appropriate without invoking the full tool loop.
    """
    session = SessionLocal()
    try:
        ct = ConversationTurn(
            call_id=call_id,
            speaker=("AGENT" if role == "agent" else "CUSTOMER"),
            text=text,
            timestamp=datetime.now(timezone.utc),
        )
        session.add(ct)
        session.commit()
    finally:
        session.close()
