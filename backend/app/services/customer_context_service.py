from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer_models import Call, CallOutcome, CallMetric, Customer, Loan, Payment


class CustomerContextService:
    def __init__(self, db: Session):
        self.db = db

    def get_full_customer_context(self, customer_id: int) -> dict[str, Any]:
        customer = self.db.get(Customer, customer_id)
        if customer is None:
            raise ValueError("Customer not found")

        loans = self.db.execute(
            select(Loan)
            .where(Loan.customer_id == customer_id)
            .order_by(Loan.due_date.asc())
        ).scalars().all()

        loan_ids = [loan.id for loan in loans]

        payments_by_loan_id: dict[int, list[dict[str, Any]]] = {}
        if loan_ids:
            payments = self.db.execute(
                select(Payment)
                .where(Payment.loan_id.in_(loan_ids))
                .order_by(Payment.payment_date.desc())
            ).scalars().all()
            for payment in payments:
                payments_by_loan_id.setdefault(payment.loan_id, []).append({
                    "id": payment.id,
                    "amount": str(payment.amount),
                    "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
                    "payment_method": payment.payment_method,
                    "status": payment.status,
                    "transaction_reference": payment.transaction_reference,
                })

        calls = self.db.execute(
            select(Call)
            .where(Call.customer_id == customer_id)
            .order_by(Call.started_at.desc())
        ).scalars().all()

        call_ids = [call.id for call in calls]
        outcomes_by_call_id: dict[int, dict[str, Any]] = {}
        if call_ids:
            outcomes = self.db.execute(
                select(CallOutcome).where(CallOutcome.call_id.in_(call_ids))
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

        metrics_by_call_id: dict[int, dict[str, Any]] = {}
        if call_ids:
            metrics = self.db.execute(
                select(CallMetric).where(CallMetric.call_id.in_(call_ids))
            ).scalars().all()
            for metric in metrics:
                metrics_by_call_id[metric.call_id] = {
                    "id": metric.id,
                    "call_id": metric.call_id,
                    "total_turns": metric.total_turns,
                    "user_turns": metric.user_turns,
                    "agent_turns": metric.agent_turns,
                    "tool_calls": metric.tool_calls,
                    "tool_failures": metric.tool_failures,
                    "avg_response_latency_ms": str(metric.avg_response_latency_ms) if metric.avg_response_latency_ms is not None else None,
                }

        previous_calls = []
        for call in calls:
            previous_calls.append({
                "id": call.id,
                "started_at": call.started_at.isoformat() if call.started_at else None,
                "ended_at": call.ended_at.isoformat() if call.ended_at else None,
                "duration_seconds": call.duration_seconds,
                "status": call.status,
                "agent_id": call.agent_id,
                "outcome": outcomes_by_call_id.get(call.id),
                "metric": metrics_by_call_id.get(call.id),
            })

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
