from fastapi import APIRouter, HTTPException

from app.schemas.agent import AgentTestRequest, AgentTestResponse, GeminiHealthResponse
from app.services.gemini_service import GeminiConfigError, GeminiService

router = APIRouter(prefix="/api/v1", tags=["agent"])

BANKING_SYSTEM_INSTRUCTIONS = (
    "You are a helpful banking follow-up agent. "
    "You speak clearly, empathetically, and professionally. "
    "Keep responses concise and customer-friendly. "
    "Do not invent loan details or payment amounts unless they are explicitly provided. "
    "When a customer says they cannot pay, acknowledge it, resolve with empathy, and suggest a next step such as a callback, repayment plan, or verification of payment timing."
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
