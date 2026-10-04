import json
import logging
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from livekit.api import (
    AccessToken,
    CreateAgentDispatchRequest,
    CreateRoomRequest,
    ListRoomsRequest,
    LiveKitAPI,
    VideoGrants,
)

from app.db import get_db
from app.schemas.agent import (
    AgentConversationRequest,
    AgentConversationResponse,
    AgentTestRequest,
    AgentTestResponse,
    GeminiHealthResponse,
)
from app.schemas.call_lifecycle import (
    CallMessageRequest,
    CallMessageResponse,
    EndCallRequest,
    EndCallResponse,
    StartCallRequest,
    StartCallResponse,
    VoiceJoinResponse,
)
from app.models.customer_models import Call, Customer
from app.services.call_lifecycle_service import CallLifecycleService
from app.services.gemini_service import GeminiConfigError, GeminiService

router = APIRouter(prefix="/api/v1", tags=["agent"])
logger = logging.getLogger(__name__)

BANKING_SYSTEM_INSTRUCTIONS = (
    "You are a helpful banking follow-up agent. "
    "You speak clearly, empathetically, and professionally. "
    "Keep responses concise and customer-friendly. "
    "Do not invent loan details or payment amounts unless they are explicitly provided. "
    "When a customer says they cannot pay, acknowledge it, resolve with empathy, and suggest a next step such as a callback, repayment plan, or verification of payment timing. "
    "Use tools when the conversation needs customer, loan, payment, or call details before answering."
)


@router.post("/agent/calls/start", response_model=StartCallResponse)
def start_call(payload: StartCallRequest, db: Session = Depends(get_db)):
    try:
        service = CallLifecycleService(db)
        result = service.start_call(payload.customer_id)
        return {
            "call_id": result["call_id"],
            "customer": result["customer"],
            "strategy": result["strategy"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start call: {str(exc)}") from exc


@router.post("/agent/calls/{call_id}/voice", response_model=VoiceJoinResponse)
async def start_voice_session(call_id: int, db: Session = Depends(get_db)):
    """Create a room/agent dispatch and return a short-lived room-scoped token."""
    call = db.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    if call.status not in {"INITIATED", "IN_PROGRESS"}:
        raise HTTPException(status_code=409, detail="Call is no longer active")

    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    if not (livekit_url and api_key and api_secret):
        raise HTTPException(status_code=503, detail="LiveKit is not configured")

    customer = db.get(Customer, call.customer_id)
    room_name = f"followup-call-{call_id}"
    livekit = LiveKitAPI(url=livekit_url, api_key=api_key, api_secret=api_secret)
    room_created = False
    try:
        existing_rooms = await livekit.room.list_rooms(ListRoomsRequest(names=[room_name]))
        if not existing_rooms.rooms:
            await livekit.room.create_room(
                CreateRoomRequest(name=room_name, empty_timeout=120, max_participants=4)
            )
            room_created = True
            await livekit.agent_dispatch.create_dispatch(
                CreateAgentDispatchRequest(
                    agent_name="followup-voice-agent",
                    room=room_name,
                    metadata=json.dumps({"call_id": call_id, "customer_id": call.customer_id}),
                )
            )

        token = (
            AccessToken(api_key, api_secret)
            .with_identity(f"customer-{call.customer_id}")
            .with_name(customer.full_name if customer else f"Customer {call.customer_id}")
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
            .with_ttl(timedelta(minutes=30))
            .to_jwt()
        )
        return {
            "call_id": call_id,
            "room_name": room_name,
            "livekit_url": livekit_url,
            "token": token,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Could not prepare LiveKit room for call %s", call_id)
        if room_created:
            try:
                from livekit.api import DeleteRoomRequest

                await livekit.room.delete_room(DeleteRoomRequest(room=room_name))
            except Exception:
                pass
        raise HTTPException(status_code=502, detail="Could not prepare the LiveKit call") from exc
    finally:
        await livekit.aclose()


@router.post("/agent/calls/{call_id}/message", response_model=CallMessageResponse)
def send_message_to_call(call_id: int, payload: CallMessageRequest, db: Session = Depends(get_db)):
    try:
        service = CallLifecycleService(db)
        result = service.handle_message(call_id, payload.message)
        return {
            "call_id": result["call_id"],
            "response": result["response"],
            "turn_number": result["turn_number"],
            "tool_calls": result.get("tool_calls", []),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(exc)}") from exc


@router.post("/agent/calls/{call_id}/end", response_model=EndCallResponse)
def end_call(call_id: int, payload: EndCallRequest | None = None, db: Session = Depends(get_db)):
    try:
        service = CallLifecycleService(db)
        summary = payload.summary if payload else None
        result = service.end_call(call_id, summary=summary)
        return {
            "call_id": result["call_id"],
            "status": result["status"],
            "outcome": result["outcome"],
            "metrics": result["metrics"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to end call: {str(exc)}") from exc


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
        if payload.call_id is not None:
            call_service = CallLifecycleService(db)
            result = call_service.handle_message(payload.call_id, payload.message, conversation_history=payload.conversation_history)
            return {
                "response": result["response"],
                "model": service.model_name,
                "status": "ok",
                "tool_calls": result.get("tool_calls", []),
                "tool_rounds": 1,
            }

        if payload.customer_id is None:
            raise ValueError("customer_id is required for a new conversation")

        call_service = CallLifecycleService(db)
        start_result = call_service.start_call(payload.customer_id)
        result = call_service.handle_message(start_result["call_id"], payload.message, conversation_history=payload.conversation_history)
        return {
            "response": result["response"],
            "model": service.model_name,
            "status": "ok",
            "tool_calls": result.get("tool_calls", []),
            "tool_rounds": 1,
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
