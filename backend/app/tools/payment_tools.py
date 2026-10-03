from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer_models import Call, CallEvent, CallOutcome, Customer, Loan, Payment


class ToolValidationError(ValueError):
    pass


def record_payment_commitment(
    db: Session,
    *,
    call_id: int,
    loan_id: int,
    commitment_date: date,
    amount: Decimal | str | float,
    notes: str,
) -> dict[str, Any]:
    if call_id is None:
        raise ToolValidationError("call_id is required")
    if loan_id is None:
        raise ToolValidationError("loan_id is required")
    if not notes or not notes.strip():
        raise ToolValidationError("notes is required")

    call = db.get(Call, call_id)
    if call is None:
        raise ToolValidationError("Call not found")

    loan = db.get(Loan, loan_id)
    if loan is None:
        raise ToolValidationError("Loan not found")

    if loan.customer_id != call.customer_id:
        raise ToolValidationError("Loan does not belong to this customer")

    amount_decimal = Decimal(str(amount))
    if amount_decimal <= 0:
        raise ToolValidationError("commitment amount must be positive")

    if not isinstance(commitment_date, date):
        raise ToolValidationError("commitment_date must be a valid date")

    outcome = db.execute(
        select(CallOutcome).where(CallOutcome.call_id == call_id)
    ).scalar_one_or_none()

    if outcome is None:
        outcome = CallOutcome(
            call_id=call_id,
            outcome_type="PROMISE_TO_PAY",
            notes=notes,
        )
        db.add(outcome)
    else:
        outcome.outcome_type = "PROMISE_TO_PAY"
        if outcome.notes:
            outcome.notes = f"{outcome.notes}\n{notes}"
        else:
            outcome.notes = notes

    if outcome.promised_amount is None:
        outcome.promised_amount = amount_decimal
    else:
        outcome.promised_amount = Decimal(str(outcome.promised_amount)) + amount_decimal

    if outcome.promised_date is None:
        outcome.promised_date = commitment_date

    db.add(
        CallEvent(
            call_id=call_id,
            event_type="TOOL_CALLED",
            metadata_json={
                "tool": "record_payment_commitment",
                "loan_id": loan_id,
                "amount": str(amount_decimal),
                "commitment_date": commitment_date.isoformat(),
                "notes": notes,
            },
        )
    )

    db.commit()
    return {
        "call_id": call_id,
        "loan_id": loan_id,
        "commitment_date": commitment_date.isoformat(),
        "amount": str(amount_decimal),
        "status": "recorded",
    }


def get_payment_history(db: Session, loan_id: int) -> list[dict[str, Any]]:
    if loan_id is None:
        raise ToolValidationError("loan_id is required")

    loan = db.get(Loan, loan_id)
    if loan is None:
        raise ToolValidationError("Loan not found")

    payments = db.execute(
        select(Payment)
        .where(Payment.loan_id == loan_id)
        .order_by(Payment.payment_date.desc())
    ).scalars().all()

    return [
        {
            "id": payment.id,
            "amount": str(payment.amount),
            "payment_date": payment.payment_date.isoformat(),
            "payment_method": payment.payment_method,
            "status": payment.status,
            "transaction_reference": payment.transaction_reference,
        }
        for payment in payments
    ]
