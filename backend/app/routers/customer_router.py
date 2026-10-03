from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.customer import CustomerContextResponse, CustomerListResponse, CustomerRead
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=CustomerListResponse)
def list_customers(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
):
    service = CustomerService(db)
    items, total = service.get_customers(limit=limit, offset=offset)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    service = CustomerService(db)
    customer = service.get_customer_by_id(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/{customer_id}/context", response_model=CustomerContextResponse)
def get_customer_context(customer_id: int, db: Session = Depends(get_db)):
    service = CustomerService(db)
    context = service.get_customer_context_safe(customer_id)
    return {
        "customer": context["customer"],
        "loans": context["loans"],
        "payments": context["payments"],
        "previous_calls": context["previous_calls"],
    }
