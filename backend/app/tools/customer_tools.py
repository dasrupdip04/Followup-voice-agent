from __future__ import annotations

import inspect
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer_models import Call, CallOutcome, Customer, Loan, Payment


class ToolValidationError(ValueError):
    pass


def _normalize_customer_id(value: Any, *, field_name: str) -> int:
    if value is None:
        raise ToolValidationError(f"{field_name} is required")

    if isinstance(value, str):
        candidate = value.strip()
        if candidate.lower() in {"current_customer", "current customer", "customer"}:
            raise ToolValidationError(
                f"{field_name} is managed by the trusted conversation context and must not be provided by Gemini"
            )
        try:
            return int(candidate)
        except (TypeError, ValueError) as exc:
            raise ToolValidationError(f"{field_name} must be an integer") from exc

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ToolValidationError(f"{field_name} must be an integer") from exc


def _resolve_customer_id(customer_id: int | None, *, trusted_customer_id: int | None) -> int:
    resolved = trusted_customer_id if trusted_customer_id is not None else customer_id
    return _normalize_customer_id(resolved, field_name="customer_id")


def _resolve_loan_for_customer(db: Session, loan_id: int, *, trusted_customer_id: int | None) -> Loan:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise ToolValidationError("Loan not found")

    if trusted_customer_id is not None:
        customer_id = _normalize_customer_id(trusted_customer_id, field_name="customer_id")
        if loan.customer_id != customer_id:
            raise ToolValidationError("Loan does not belong to the current customer")

    return loan


def get_customer_profile(
    db: Session,
    customer_id: int | None = None,
    *,
    _trusted_customer_id: int | None = None,
) -> dict[str, Any]:
    """Return the current customer's profile. Use the active customer context already set by the backend; do not pass customer_id."""
    resolved_customer_id = _resolve_customer_id(customer_id, trusted_customer_id=_trusted_customer_id)

    customer = db.get(Customer, resolved_customer_id)
    if customer is None:
        raise ToolValidationError("Customer not found")

    return {
        "id": customer.id,
        "customer_number": customer.customer_number,
        "full_name": customer.full_name,
        "city": customer.city,
        "bank_name": customer.bank_name,
        "preferred_language": customer.preferred_language,
        "phone_number": customer.phone_number,
    }


get_customer_profile.__signature__ = inspect.Signature(
    parameters=[inspect.Parameter("db", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Session)],
    return_annotation=dict[str, Any],
)


def get_customer_loans(
    db: Session,
    customer_id: int | None = None,
    *,
    _trusted_customer_id: int | None = None,
) -> list[dict[str, Any]]:
    """Return all loans for the active customer. This tool uses the trusted current customer from the conversation context."""
    resolved_customer_id = _resolve_customer_id(customer_id, trusted_customer_id=_trusted_customer_id)

    customer = db.get(Customer, resolved_customer_id)
    if customer is None:
        raise ToolValidationError("Customer not found")

    loans = db.execute(
        select(Loan)
        .where(Loan.customer_id == resolved_customer_id)
        .order_by(Loan.due_date.asc())
    ).scalars().all()

    return [
        {
            "id": loan.id,
            "loan_number": loan.loan_number,
            "loan_type": loan.loan_type,
            "outstanding_amount": str(loan.outstanding_amount),
            "due_date": loan.due_date.isoformat() if loan.due_date else None,
            "status": loan.status,
        }
        for loan in loans
    ]


get_customer_loans.__signature__ = inspect.Signature(
    parameters=[inspect.Parameter("db", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Session)],
    return_annotation=list[dict[str, Any]],
)


def get_loan_details(
    db: Session,
    loan_id: int,
    customer_id: int | None = None,
    *,
    _trusted_customer_id: int | None = None,
) -> dict[str, Any]:
    """Return a loan record only when the loan belongs to the active customer. Provide loan_id only; do not pass customer_id."""
    if loan_id is None:
        raise ToolValidationError("loan_id is required")

    loan = _resolve_loan_for_customer(db, int(loan_id), trusted_customer_id=_trusted_customer_id)

    return {
        "id": loan.id,
        "customer_id": loan.customer_id,
        "loan_number": loan.loan_number,
        "loan_type": loan.loan_type,
        "principal_amount": str(loan.principal_amount),
        "outstanding_amount": str(loan.outstanding_amount),
        "interest_rate": str(loan.interest_rate),
        "emi_amount": str(loan.emi_amount),
        "due_date": loan.due_date.isoformat(),
        "status": loan.status,
    }


get_loan_details.__signature__ = inspect.Signature(
    parameters=[
        inspect.Parameter("db", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Session),
        inspect.Parameter("loan_id", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int),
    ],
    return_annotation=dict[str, Any],
)


def get_payment_history(
    db: Session,
    loan_id: int,
    customer_id: int | None = None,
    *,
    _trusted_customer_id: int | None = None,
) -> list[dict[str, Any]]:
    """Return payment history for a loan only if it belongs to the active customer. Provide loan_id only; do not pass customer_id."""
    if loan_id is None:
        raise ToolValidationError("loan_id is required")

    loan = _resolve_loan_for_customer(db, int(loan_id), trusted_customer_id=_trusted_customer_id)

    payments = db.execute(
        select(Payment)
        .where(Payment.loan_id == loan.id)
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


get_payment_history.__signature__ = inspect.Signature(
    parameters=[
        inspect.Parameter("db", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Session),
        inspect.Parameter("loan_id", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int),
    ],
    return_annotation=list[dict[str, Any]],
)


def get_customer_call_history(
    db: Session,
    customer_id: int | None = None,
    *,
    _trusted_customer_id: int | None = None,
) -> list[dict[str, Any]]:
    """Return recent calls for the active customer. Use the trusted conversation customer automatically; do not supply customer_id."""
    resolved_customer_id = _resolve_customer_id(customer_id, trusted_customer_id=_trusted_customer_id)

    customer = db.get(Customer, resolved_customer_id)
    if customer is None:
        raise ToolValidationError("Customer not found")

    calls = db.execute(
        select(Call)
        .where(Call.customer_id == resolved_customer_id)
        .order_by(Call.started_at.desc())
    ).scalars().all()

    result = []
    for call in calls:
        result.append(
            {
                "id": call.id,
                "started_at": call.started_at.isoformat(),
                "ended_at": call.ended_at.isoformat() if call.ended_at else None,
                "duration_seconds": call.duration_seconds,
                "status": call.status,
                "agent_id": call.agent_id,
            }
        )
    return result


get_customer_call_history.__signature__ = inspect.Signature(
    parameters=[inspect.Parameter("db", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Session)],
    return_annotation=list[dict[str, Any]],
)


def get_customer_context(
    db: Session,
    customer_id: int | None = None,
    *,
    _trusted_customer_id: int | None = None,
) -> dict[str, Any]:
    """Return the complete customer context for the active conversation: profile, loans, and recent payments. Do not provide customer_id."""
    resolved_customer_id = _resolve_customer_id(customer_id, trusted_customer_id=_trusted_customer_id)

    customer = db.get(Customer, resolved_customer_id)
    if customer is None:
        raise ToolValidationError("Customer not found")

    loans = db.execute(
        select(Loan)
        .where(Loan.customer_id == resolved_customer_id)
        .order_by(Loan.due_date.asc())
    ).scalars().all()

    loan_ids = [loan.id for loan in loans]
    payments: list[Payment] = []
    if loan_ids:
        payments = db.execute(
            select(Payment)
            .where(Payment.loan_id.in_(loan_ids))
            .order_by(Payment.payment_date.desc())
        ).scalars().all()

    return {
        "customer": {
            "id": customer.id,
            "customer_number": customer.customer_number,
            "full_name": customer.full_name,
            "city": customer.city,
            "bank_name": customer.bank_name,
            "preferred_language": customer.preferred_language,
            "phone_number": customer.phone_number,
        },
        "loans": [
            {
                "id": loan.id,
                "loan_number": loan.loan_number,
                "loan_type": loan.loan_type,
                "outstanding_amount": str(loan.outstanding_amount),
                "due_date": loan.due_date.isoformat(),
                "status": loan.status,
            }
            for loan in loans
        ],
        "recent_payments": [
            {
                "loan_id": payment.loan_id,
                "amount": str(payment.amount),
                "payment_date": payment.payment_date.isoformat(),
                "payment_method": payment.payment_method,
                "status": payment.status,
            }
            for payment in payments[:10]
        ],
    }


get_customer_context.__signature__ = inspect.Signature(
    parameters=[inspect.Parameter("db", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Session)],
    return_annotation=dict[str, Any],
)


def get_full_customer_context(db: Session, customer_id: int) -> dict[str, Any]:
    """Return the complete current customer context in one backend query: profile, loans, payment history, and prior call metadata. Use this instead of multiple separate customer/loan/payment read tools when the full context is needed."""
    if customer_id is None:
        raise ToolValidationError("customer_id is required")

    customer = db.get(Customer, customer_id)
    if customer is None:
        raise ToolValidationError("Customer not found")

    loans = db.execute(
        select(Loan)
        .where(Loan.customer_id == customer_id)
        .order_by(Loan.due_date.asc())
    ).scalars().all()

    loan_ids = [loan.id for loan in loans]
    payments_by_loan_id: dict[int, list[dict[str, Any]]] = {}
    if loan_ids:
        payments = db.execute(
            select(Payment)
            .where(Payment.loan_id.in_(loan_ids))
            .order_by(Payment.payment_date.desc())
        ).scalars().all()
        for payment in payments:
            payments_by_loan_id.setdefault(payment.loan_id, []).append(
                {
                    "id": payment.id,
                    "amount": str(payment.amount),
                    "payment_date": payment.payment_date.isoformat(),
                    "payment_method": payment.payment_method,
                    "status": payment.status,
                    "transaction_reference": payment.transaction_reference,
                }
            )

    calls = db.execute(
        select(Call)
        .where(Call.customer_id == customer_id)
        .order_by(Call.started_at.desc())
    ).scalars().all()

    call_ids = [call.id for call in calls]
    outcomes_by_call_id: dict[int, dict[str, Any]] = {}
    if call_ids:
        outcomes = db.execute(
            select(CallOutcome)
            .where(CallOutcome.call_id.in_(call_ids))
        ).scalars().all()
        for outcome in outcomes:
            outcomes_by_call_id[outcome.call_id] = {
                "id": outcome.id,
                "call_id": outcome.call_id,
                "outcome_type": outcome.outcome_type,
                "promised_amount": str(outcome.promised_amount) if outcome.promised_amount is not None else None,
                "promised_date": outcome.promised_date.isoformat() if outcome.promised_date else None,
                "notes": outcome.notes,
            }

    previous_calls = []
    for call in calls:
        previous_calls.append(
            {
                "id": call.id,
                "started_at": call.started_at.isoformat(),
                "ended_at": call.ended_at.isoformat() if call.ended_at else None,
                "duration_seconds": call.duration_seconds,
                "status": call.status,
                "agent_id": call.agent_id,
                "outcome": outcomes_by_call_id.get(call.id),
            }
        )

    return {
        "customer": {
            "id": customer.id,
            "customer_number": customer.customer_number,
            "full_name": customer.full_name,
            "city": customer.city,
            "bank_name": customer.bank_name,
            "preferred_language": customer.preferred_language,
            "phone_number": customer.phone_number,
        },
        "active_loans": [
            {
                "id": loan.id,
                "loan_number": loan.loan_number,
                "loan_type": loan.loan_type,
                "status": loan.status,
                "outstanding_amount": str(loan.outstanding_amount),
                "due_date": loan.due_date.isoformat() if loan.due_date else None,
                "principal_amount": str(loan.principal_amount),
                "interest_rate": str(loan.interest_rate),
                "emi_amount": str(loan.emi_amount),
            }
            for loan in loans
        ],
        "loan_payment_history": payments_by_loan_id,
        "previous_calls": previous_calls,
        "customer_summary": {
            "loan_count": len(loans),
            "total_outstanding": str(sum(float(loan.outstanding_amount) for loan in loans)),
            "active_overdue_loans": sum(1 for loan in loans if loan.status == "OVERDUE"),
        },
    }


get_full_customer_context.__signature__ = inspect.Signature(
    parameters=[inspect.Parameter("db", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Session)],
    return_annotation=dict[str, Any],
)
