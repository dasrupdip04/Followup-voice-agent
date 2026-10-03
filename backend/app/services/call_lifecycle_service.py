from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer_models import Call, CallEvent, CallMetric, CallOutcome, ConversationTurn, Customer
from app.services.call_strategy_service import CallStrategyService
from app.services.conversation_state import ConversationState, ConversationStateStore
from app.services.customer_context_service import CustomerContextService
from app.tools.customer_tools import get_full_customer_context


class CallLifecycleService:
    def __init__(self, db: Session):
        self.db = db
        self.state_store = ConversationStateStore()

    def start_call(self, customer_id: int) -> dict[str, Any]:
        customer = self.db.get(Customer, customer_id)
        if customer is None:
            raise ValueError("Customer not found")

        context_service = CustomerContextService(self.db)
        customer_context = context_service.get_full_customer_context(customer_id)

        strategy_service = CallStrategyService()
        strategy = strategy_service.generate_strategy(customer_context)

        call = Call(
            customer_id=customer_id,
            started_at=datetime.utcnow(),
            status="INITIATED",
            agent_id="followup-agent",
        )
        self.db.add(call)
        self.db.flush()

        state = ConversationState(
            customer_id=customer_id,
            call_id=call.id,
            customer_context=customer_context,
            call_strategy=strategy,
            current_objective=strategy.get("objective"),
            next_action="Begin collections follow-up",
            turn_count=0,
            started_at=call.started_at,
        )
        self.state_store.store(state)

        self.db.add(
            CallEvent(
                call_id=call.id,
                event_type="CALL_STARTED",
                metadata_json={
                    "customer_id": customer_id,
                    "strategy": strategy,
                },
            )
        )
        self.db.commit()

        return {
            "call_id": call.id,
            "customer": customer_context["customer"],
            "strategy": strategy,
        }

    def _load_state(self, call_id: int) -> ConversationState:
        state = self.state_store.get_by_call_id(call_id)
        if state is None:
            call = self.db.get(Call, call_id)
            if call is None:
                raise ValueError("Call not found")
            state = ConversationState(
                customer_id=call.customer_id,
                call_id=call.id,
                customer_context={},
                started_at=call.started_at or datetime.utcnow(),
                call_strategy={},
            )
            self.state_store.store(state)
        return state

    def handle_message(self, call_id: int, message: str, conversation_history: list[dict[str, str]] | None = None) -> dict[str, Any]:
        state = self._load_state(call_id)
        call = self.db.get(Call, call_id)
        if call is None:
            raise ValueError("Call not found")
        if call.status != "IN_PROGRESS":
            call.status = "IN_PROGRESS"

        if not state.customer_context:
            ctx_service = CustomerContextService(self.db)
            state.customer_context = ctx_service.get_full_customer_context(state.customer_id)
        if not state.call_strategy:
            strategy_service = CallStrategyService()
            state.call_strategy = strategy_service.generate_strategy(state.customer_context)
            state.current_objective = state.call_strategy.get("objective")
        if conversation_history:
            state.conversation_history = conversation_history[:]

        state.turn_count += 1
        state.conversation_history.append({"speaker": "CUSTOMER", "text": message})

        service = __import__('app.services.gemini_service', fromlist=['GeminiService']).GeminiService()
        response = service.process_with_tools(
            system_instructions=(
                "You are a banking collections follow-up assistant. "
                "Use only facts from the supplied customer context and conversation history. "
                "Answer plainly, empathetically, and do not fabricate obligations, amounts, or promises. "
                "You may call backend tools only when necessary for missing data."
            ),
            conversation_history=state.conversation_history,
            current_message=message,
            customer_context={
                "customer": state.customer_context.get("customer"),
                "strategy": state.call_strategy,
                "summary": state.customer_context.get("customer_summary"),
            },
            max_tool_rounds=1,
            db=self.db,
            trusted_customer_id=state.customer_id,
        )

        assistant_text = response["response"]
        state.conversation_history.append({"speaker": "AGENT", "text": assistant_text})
        state.tool_calls = response.get("tool_calls", [])
        state.next_action = state.call_strategy.get("payment_commitment_goal") if state.call_strategy else None

        self.db.add(ConversationTurn(call_id=call_id, speaker="CUSTOMER", text=message, timestamp=datetime.utcnow()))
        self.db.add(ConversationTurn(call_id=call_id, speaker="AGENT", text=assistant_text, timestamp=datetime.utcnow()))
        self.db.flush()
        self.db.add(
            CallEvent(
                call_id=call_id,
                event_type="MESSAGE_RECEIVED",
                metadata_json={
                    "message": message,
                    "response": assistant_text,
                    "tool_calls": response.get("tool_calls", []),
                },
            )
        )
        self.db.commit()

        return {
            "call_id": call_id,
            "response": assistant_text,
            "turn_number": state.turn_count,
            "tool_calls": response.get("tool_calls", []),
        }

    def end_call(self, call_id: int, summary: str | None = None) -> dict[str, Any]:
        state = self._load_state(call_id)
        call = self.db.get(Call, call_id)
        if call is None:
            raise ValueError("Call not found")
        if call.status == "COMPLETED":
            existing_outcome = self.db.execute(
                select(CallOutcome).where(CallOutcome.call_id == call_id)
            ).scalar_one_or_none()
            existing_metric = self.db.execute(
                select(CallMetric).where(CallMetric.call_id == call_id)
            ).scalar_one_or_none()
            return {
                "call_id": call_id,
                "status": "already_completed",
                "outcome": {
                    "outcome_type": existing_outcome.outcome_type if existing_outcome else None,
                    "notes": existing_outcome.notes if existing_outcome else None,
                },
                "metrics": {
                    "total_turns": existing_metric.total_turns if existing_metric else len(state.conversation_history),
                    "tool_calls": existing_metric.tool_calls if existing_metric else len(state.tool_calls),
                },
            }

        call.status = "COMPLETED"
        call.ended_at = datetime.utcnow()
        if call.started_at:
            call.duration_seconds = int((call.ended_at - call.started_at).total_seconds())

        final_analysis = self._generate_final_analysis(call_id, state)

        outcome = CallOutcome(
            call_id=call_id,
            outcome_type=final_analysis.get("outcome") or "CALLBACK_REQUESTED",
            notes=final_analysis.get("summary") or summary,
            promised_amount=final_analysis.get("commitment_amount"),
            promised_date=final_analysis.get("commitment_date"),
        )
        self.db.add(outcome)

        metric = CallMetric(
            call_id=call_id,
            total_turns=state.turn_count,
            user_turns=sum(1 for turn in state.conversation_history if turn.get("speaker") == "CUSTOMER"),
            agent_turns=sum(1 for turn in state.conversation_history if turn.get("speaker") == "AGENT"),
            avg_response_latency_ms=None,
            avg_stt_latency_ms=None,
            avg_llm_latency_ms=None,
            avg_tts_latency_ms=None,
            user_interruptions=0,
            agent_interruptions=0,
            tool_calls=len(state.tool_calls),
            tool_failures=0,
            tokens_input=0,
            tokens_output=0,
        )
        self.db.add(metric)

        self.db.add(
            CallEvent(
                call_id=call_id,
                event_type="CALL_ENDED",
                metadata_json={
                    "summary": final_analysis.get("summary"),
                    "outcome": final_analysis.get("outcome"),
                    "promise_to_pay": final_analysis.get("promise_to_pay"),
                    "follow_up_required": final_analysis.get("follow_up_required"),
                },
            )
        )
        self.db.commit()

        self.state_store.clear_call(call_id)

        return {
            "call_id": call_id,
            "status": "completed",
            "outcome": final_analysis,
            "metrics": {
                "duration_seconds": call.duration_seconds,
                "total_turns": state.turn_count,
                "tool_calls": len(state.tool_calls),
            },
        }

    @staticmethod
    def _parse_analysis_response(raw_text: str | Any) -> dict[str, Any]:
        if raw_text is None:
            raise ValueError("Gemini returned no final analysis")

        text = str(raw_text).strip()
        if not text:
            raise ValueError("Gemini returned an empty analysis")

        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].lstrip()

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        raise ValueError(f"Gemini returned malformed final-analysis JSON: {text[:300]}")

    def _generate_final_analysis(self, call_id: int, state: ConversationState) -> dict[str, Any]:
        service = CallStrategyService()
        raw = {
            "customer_context": state.customer_context,
            "conversation_history": state.conversation_history,
            "call_strategy": state.call_strategy,
            "collected_information": state.collected_information,
            "commitments": state.commitments,
            "objections": state.objections,
            "next_action": state.next_action,
        }

        response = service.client.models.generate_content(
            model=service.model_name,
            contents=(
                "Analyze the completed banking collections conversation and produce JSON only. "
                "Use facts from the supplied conversation only. If something is unknown, use null. "
                "Return keys: outcome, payment_commitment, commitment_amount, commitment_date, reason_for_nonpayment, objection, customer_sentiment, cooperation_level, promise_to_pay, follow_up_required, escalation_required, summary, key_events. "
                f"Conversation data: {raw}"
            ),
            config=__import__('google.genai.types', fromlist=['GenerateContentConfig']).GenerateContentConfig(
                temperature=0.2,
                top_p=0.8,
                max_output_tokens=512,
            ),
        )

        text = getattr(response, "text", None)
        if text is None:
            candidates = getattr(response, "candidates", None) or []
            if candidates:
                first = candidates[0]
                parts = getattr(first, "content", None)
                if parts is not None and hasattr(parts, "parts"):
                    assembled = []
                    for part in parts.parts:
                        if hasattr(part, "text") and part.text:
                            assembled.append(part.text)
                    text = "".join(assembled)

        if not text:
            return {
                "outcome": "UNKNOWN",
                "payment_commitment": None,
                "commitment_amount": None,
                "commitment_date": None,
                "reason_for_nonpayment": None,
                "objection": None,
                "customer_sentiment": None,
                "cooperation_level": None,
                "promise_to_pay": None,
                "follow_up_required": None,
                "escalation_required": None,
                "summary": "Conversation ended.",
                "key_events": [],
            }

        try:
            return self._parse_analysis_response(text)
        except ValueError:
            return {
                "outcome": "CALLBACK_REQUESTED",
                "payment_commitment": None,
                "commitment_amount": None,
                "commitment_date": None,
                "reason_for_nonpayment": None,
                "objection": None,
                "customer_sentiment": None,
                "cooperation_level": "unknown",
                "promise_to_pay": False,
                "follow_up_required": True,
                "escalation_required": False,
                "summary": "Conversation ended without a structured summary from the model.",
                "key_events": [],
            }
