from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.agent import GeminiHealthResponse
from app.services.gemini_service import GeminiConfigError, GeminiService

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
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


@router.get("/health/gemini", response_model=GeminiHealthResponse)
def health_gemini() -> dict[str, object]:
    try:
        service = GeminiService()
        return {
            "status": "ok",
            "configured": True,
            "model": service.model_name,
        }
    except GeminiConfigError:
        return {
            "status": "error",
            "configured": False,
            "model": None,
        }
