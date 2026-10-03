from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.customer_models import Call, CallMetric, CallOutcome, Customer, Loan, Payment


class CustomerService:
    def __init__(self, db: Session):
        self.db = db

    def get_customers(self, limit: int, offset: int) -> tuple[list[Customer], int]:
        query = select(Customer).order_by(Customer.id.asc()).limit(limit).offset(offset)
        items = self.db.execute(query).scalars().all()
        total = self.db.scalar(select(func.count(Customer.id)))
        return list(items), total

    def get_customer_by_id(self, customer_id: int) -> Customer | None:
        return self.db.get(Customer, customer_id)

    def get_customer_context(self, customer_id: int) -> dict[str, Any]:
        customer = self.db.get(Customer, customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")

        loans = self.db.execute(
            select(Loan).where(Loan.customer_id == customer_id).order_by(Loan.due_date.asc())
        ).scalars().all()

        loan_ids = [loan.id for loan in loans]
        payments = []
        if loan_ids:
            payments = self.db.execute(
                select(Payment)
                .where(Payment.loan_id.in_(loan_ids))
                .order_by(Payment.payment_date.desc())
            ).scalars().all()

        calls = self.db.execute(
            select(Call)
            .where(Call.customer_id == customer_id)
            .order_by(Call.started_at.desc())
        ).scalars().all()

        call_ids = [call.id for call in calls]
        outcomes_by_call_id = {}
        if call_ids:
            outcomes = self.db.execute(
                select(CallOutcome).where(CallOutcome.call_id.in_(call_ids))
            ).scalars().all()
            outcomes_by_call_id = {outcome.call_id: outcome for outcome in outcomes}

        metrics_by_call_id = {}
        if call_ids:
            metrics = self.db.execute(
                select(CallMetric).where(CallMetric.call_id.in_(call_ids))
            ).scalars().all()
            metrics_by_call_id = {metric.call_id: metric for metric in metrics}

        previous_calls = []
        for call in calls:
            previous_calls.append({
                "id": call.id,
                "customer_id": call.customer_id,
                "started_at": call.started_at,
                "ended_at": call.ended_at,
                "duration_seconds": call.duration_seconds,
                "status": call.status,
                "agent_id": call.agent_id,
                "created_at": call.created_at,
                "outcome": outcomes_by_call_id.get(call.id),
                "metric": metrics_by_call_id.get(call.id),
            })

        return {
            "customer": customer,
            "loans": loans,
            "payments": payments,
            "previous_calls": previous_calls,
        }

    def get_customer_context_safe(self, customer_id: int) -> dict[str, Any]:
        try:
            return self.get_customer_context(customer_id)
        except HTTPException:
            raise
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=500, detail="Database error while loading customer context") from exc
