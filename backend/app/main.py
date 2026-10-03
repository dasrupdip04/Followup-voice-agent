from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers.customer_router import router as customer_router

app = FastAPI(title="Followup Voice Agent Backend")
app.include_router(customer_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "database": "unavailable", "message": "PostgreSQL is not available."},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "database": "unavailable", "message": str(exc)},
        ) from exc
