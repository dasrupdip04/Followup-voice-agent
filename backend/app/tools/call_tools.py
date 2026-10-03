from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer_models import Call, CallEvent, CallMetric, CallOutcome, Customer, ConversationTurn


class ToolValidationError(ValueError):
    pass


def record_conversation_turn(
    db: Session,
    *,
    call_id: int,
    speaker: str,
    text: str,
    timestamp: datetime | None = None,
    latency_ms: int | None = None,
) -> dict[str, Any]:
    if call_id is None:
        raise ToolValidationError("call_id is required")
    if not speaker or speaker not in {"AGENT", "CUSTOMER"}:
        raise ToolValidationError("speaker must be AGENT or CUSTOMER")
    if not text or not text.strip():
        raise ToolValidationError("text must not be empty")

    call = db.get(Call, call_id)
    if call is None:
        raise ToolValidationError("Call not found")

    turn = ConversationTurn(
        call_id=call_id,
        speaker=speaker,
        text=text.strip(),
        timestamp=timestamp or datetime.utcnow(),
        latency_ms=latency_ms,
    )
    db.add(turn)
    db.commit()

    return {
        "call_id": call_id,
        "speaker": speaker,
        "text": text.strip(),
        "status": "recorded",
    }


def record_customer_response(
    db: Session,
    *,
    call_id: int,
    response_type: str,
    summary: str,
) -> dict[str, Any]:
    if call_id is None:
        raise ToolValidationError("call_id is required")
    if not response_type or not response_type.strip():
        raise ToolValidationError("response_type is required")
    if not summary or not summary.strip():
        raise ToolValidationError("summary is required")

    call = db.get(Call, call_id)
    if call is None:
        raise ToolValidationError("Call not found")

    outcome = db.execute(
        select(CallOutcome).where(CallOutcome.call_id == call_id)
    ).scalar_one_or_none()

    if outcome is None:
        outcome = CallOutcome(call_id=call_id, outcome_type="CALLBACK_REQUESTED", notes=summary)
        db.add(outcome)
    else:
        outcome.notes = summary
        outcome.outcome_type = outcome.outcome_type or "CALLBACK_REQUESTED"

    db.add(
        CallEvent(
            call_id=call_id,
            event_type="TOOL_CALLED",
            metadata_json={
                "tool": "record_customer_response",
                "response_type": response_type,
                "summary": summary,
            },
        )
    )

    db.commit()
    return {
        "call_id": call_id,
        "response_type": response_type,
        "summary": summary,
        "status": "recorded",
    }


def update_call_outcome(
    db: Session,
    *,
    call_id: int,
    outcome: str,
    summary: str,
    next_action: str | None,
) -> dict[str, Any]:
    if call_id is None:
        raise ToolValidationError("call_id is required")
    if not outcome or not outcome.strip():
        raise ToolValidationError("outcome is required")

    call = db.get(Call, call_id)
    if call is None:
        raise ToolValidationError("Call not found")

    allowed = {
        "PROMISE_TO_PAY",
        "PAYMENT_COMPLETED",
        "CALLBACK_REQUESTED",
        "REFUSED",
        "NO_ANSWER",
        "WRONG_NUMBER",
        "DISPUTE",
        "NEEDS_HUMAN",
    }
    if outcome not in allowed:
        raise ToolValidationError("outcome is not allowed")

    existing = db.execute(
        select(CallOutcome).where(CallOutcome.call_id == call_id)
    ).scalar_one_or_none()

    if existing is None:
        existing = CallOutcome(call_id=call_id, outcome_type=outcome, notes=summary)
        db.add(existing)
    else:
        existing.outcome_type = outcome
        existing.notes = summary

    db.add(
        CallEvent(
            call_id=call_id,
            event_type="TOOL_COMPLETED",
            metadata_json={
                "tool": "update_call_outcome",
                "next_action": next_action,
                "summary": summary,
            },
        )
    )
    db.commit()

    return {
        "call_id": call_id,
        "outcome": outcome,
        "next_action": next_action,
        "status": "updated",
    }


def save_call_event(
    db: Session,
    *,
    call_id: int,
    event_type: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if call_id is None:
        raise ToolValidationError("call_id is required")
    if not event_type or not event_type.strip():
        raise ToolValidationError("event_type is required")
    if metadata is None:
        raise ToolValidationError("metadata is required")

    call = db.get(Call, call_id)
    if call is None:
        raise ToolValidationError("Call not found")

    event = CallEvent(
        call_id=call_id,
        event_type=event_type,
        metadata_json=metadata,
    )
    db.add(event)
    db.commit()

    return {
        "call_id": call_id,
        "event_type": event_type,
        "status": "saved",
    }
