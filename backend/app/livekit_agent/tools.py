"""Lightweight wrappers to reuse Phase 5/6 backend services from the LiveKit agent.

These wrappers avoid direct SQL access and instead call the existing service
classes in the backend. They keep Gemini and tool usage minimal and reuse
the server-side validation already implemented in the call lifecycle services.
"""
from typing import Dict, Any, Optional
from datetime import datetime
from app.services.call_lifecycle_service import CallLifecycleService
from app.db import SessionLocal
from app.models.customer_models import ConversationTurn


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


def append_turn(call_id: int, role: str, text: str) -> None:
    """Persist a conversation turn directly to the `conversation_turns` table.

    This is a small helper used by the LiveKit runner to persist raw user or
    agent transcripts when appropriate without invoking the full tool loop.
    """
    session = SessionLocal()
    try:
        ct = ConversationTurn(call_id=call_id, speaker=("AGENT" if role == "agent" else "CUSTOMER"), text=text, timestamp=datetime.utcnow())
        session.add(ct)
        session.commit()
    finally:
        session.close()
