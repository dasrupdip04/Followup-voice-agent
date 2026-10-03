from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.agent import (
    AgentConversationRequest,
    AgentConversationResponse,
    AgentTestRequest,
    AgentTestResponse,
    GeminiHealthResponse,
)
from app.services.gemini_service import GeminiConfigError, GeminiService

router = APIRouter(prefix="/api/v1", tags=["agent"])

BANKING_SYSTEM_INSTRUCTIONS = (
    "You are a helpful banking follow-up agent. "
    "You speak clearly, empathetically, and professionally. "
    "Keep responses concise and customer-friendly. "
    "Do not invent loan details or payment amounts unless they are explicitly provided. "
    "When a customer says they cannot pay, acknowledge it, resolve with empathy, and suggest a next step such as a callback, repayment plan, or verification of payment timing. "
    "Use tools when the conversation needs customer, loan, payment, or call details before answering."
)


@router.post("/agent/test", response_model=AgentTestResponse)
def test_agent_generation(payload: AgentTestRequest):
    try:
        service = GeminiService()
        response_text = service.generate_agent_response(
            system_instructions=BANKING_SYSTEM_INSTRUCTIONS,
            conversation_history=payload.conversation_history,
            current_message=payload.message,
            customer_context=payload.customer_context,
        )
        return {
            "response": response_text,
            "model": service.model_name,
            "status": "ok",
        }
    except GeminiConfigError as exc:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"Gemini request failed: {str(exc)}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Gemini generation failed") from exc


@router.post("/agent/conversation", response_model=AgentConversationResponse)
def process_agent_conversation(payload: AgentConversationRequest, db: Session = Depends(get_db)):
    try:
        service = GeminiService()
        trusted_customer_id = payload.customer_id
        result = service.process_with_tools(
            system_instructions=BANKING_SYSTEM_INSTRUCTIONS,
            conversation_history=payload.conversation_history,
            current_message=payload.message,
            customer_context=payload.customer_context,
            max_tool_rounds=3,
            db=db,
            trusted_customer_id=trusted_customer_id,
        )
        return {
            "response": result["response"],
            "model": service.model_name,
            "status": result.get("status", "ok"),
            "tool_calls": result.get("tool_calls", []),
            "tool_rounds": result.get("tool_rounds", 0),
        }
    except GeminiConfigError as exc:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"Gemini request failed: {str(exc)}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Gemini conversation failed") from exc


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
