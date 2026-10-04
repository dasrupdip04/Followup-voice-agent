"""LiveKit Agents 1.8 voice worker using the verified call lifecycle."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from livekit import agents
from livekit.agents import llm
from livekit.plugins import cartesia, deepgram

from app.livekit_agent import tools as lifecycle_tools

logger = logging.getLogger(__name__)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} must be configured to start the voice worker")
    return value


def _job_call(metadata: str) -> tuple[int, int]:
    """Read the existing persisted call/customer IDs from dispatch metadata."""
    try:
        value = json.loads(metadata or "{}")
        call_id = int(value["call_id"])
        customer_id = int(value["customer_id"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError('LiveKit job metadata must contain "call_id" and "customer_id"') from exc
    if call_id < 1 or customer_id < 1:
        raise ValueError("call_id and customer_id must be positive integers")
    return call_id, customer_id


class LifecycleVoiceAgent(agents.Agent):
    """Deepgram -> existing lifecycle/Gemini tools -> Cartesia via AgentSession."""

    def __init__(self, *, call_id: int, customer_id: int, opening: str, stt: Any, tts: Any) -> None:
        super().__init__(
            instructions=(
                "Use the follow-up service's response as the only answer. "
                "Keep speech clear and concise."
            ),
            stt=stt,
            tts=tts,
            id=f"followup-call-{call_id}",
        )
        self.call_id = call_id
        self.customer_id = customer_id
        self.opening = opening

    async def on_enter(self) -> None:
        """Speak the strategy-based opening as soon as the customer joins."""
        await asyncio.to_thread(
            lifecycle_tools.append_turn,
            self.call_id,
            "agent",
            self.opening,
        )
        await self.session.say(self.opening)

    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage) -> None:
        """Send LiveKit's completed STT user turn through the existing lifecycle."""
        transcript = (new_message.text_content or new_message.raw_text_content or "").strip()
        logger.info("Call %s completed customer transcript (%d chars)", self.call_id, len(transcript))
        if not transcript:
            logger.error("Call %s completed user turn had no transcript text", self.call_id)
            return
        try:
            logger.info("Call %s invoking CallLifecycleService for customer transcript", self.call_id)
            result = await asyncio.to_thread(lifecycle_tools.handle_message_for_session, self.call_id, transcript)
            response = str(result["response"])
            logger.info(
                "Call %s lifecycle returned response (%d chars, %d tool calls)",
                self.call_id,
                len(response),
                len(result.get("tool_calls", [])),
            )
            logger.info("Call %s handing lifecycle response to LiveKit/Cartesia TTS", self.call_id)
            await self.session.say(response)
            logger.info("Call %s finished speaking lifecycle response", self.call_id)
        except Exception:
            logger.exception("Call %s lifecycle failed for completed customer transcript", self.call_id)
            raise

    async def on_exit(self) -> None:
        """Persist the normal outcome/metrics when the LiveKit session closes."""
        try:
            await asyncio.to_thread(lifecycle_tools.end_call_for_session, self.call_id)
        except Exception:
            logger.exception("Could not persist final lifecycle state for call %s", self.call_id)


async def entrypoint(ctx: agents.JobContext) -> None:
    """LiveKit Agents 1.8 room job entrypoint.

    Dispatch metadata contains the already-created call and customer IDs. The
    worker attaches to that call and never creates a second lifecycle record.
    """
    call_id, customer_id = _job_call(ctx.job.metadata)
    model = os.getenv("DEEPGRAM_MODEL", "nova-3")
    if model.startswith("flux-"):
        stt = deepgram.STTv2(model=model, api_key=_required_env("DEEPGRAM_API_KEY"))
    else:
        stt = deepgram.STT(model=model, api_key=_required_env("DEEPGRAM_API_KEY"))

    tts = cartesia.TTS(
        model=os.getenv("CARTESIA_MODEL", "sonic-3"),
        voice=_required_env("CARTESIA_VOICE_ID"),
        language=os.getenv("CARTESIA_LANGUAGE", "en"),
        api_key=_required_env("CARTESIA_API_KEY"),
    )

    call_context = await asyncio.to_thread(lifecycle_tools.get_call_context_for_voice, call_id)
    if int(call_context["customer_id"]) != customer_id:
        raise ValueError("LiveKit job customer does not match the persisted call")
    if call_context["strategy"]:
        strategy = call_context["strategy"]
        customer_name = call_context["customer_name"]
        bank_name = call_context["bank_name"]
        loan = call_context["loan"]
        if loan:
            question = next(iter(strategy.get("questions_to_ask", [])), "Is this a good time to talk?")
            opening = (
                f"Hello {customer_name}, I'm calling from {bank_name} regarding your "
                f"{loan['loan_type'].lower()} loan account {loan['loan_number']}. "
                f"The outstanding balance is ₹{loan['outstanding_amount']}. {question}"
            )
        else:
            opening = str(strategy.get("recommended_opening") or f"Hello {customer_name}, I'm calling from {bank_name}.")
    else:
        opening = "Hello, I'm calling from the bank's follow-up team. Is this a good time to talk?"

    voice_agent = LifecycleVoiceAgent(
        call_id=call_id,
        customer_id=customer_id,
        opening=opening,
        stt=stt,
        tts=tts,
    )
    session = agents.AgentSession()
    def on_transcript(ev: Any) -> None:
        logger.info(
            "Call %s STT %s transcript (%d chars): %r",
            call_id,
            "FINAL" if ev.is_final else "INTERIM",
            len(ev.transcript),
            ev.transcript[:240],
        )

    session.on("user_input_transcribed", on_transcript)
    await session.start(voice_agent, room=ctx.room, record=False)
    logger.info("Connected voice agent for call %s in room %s", call_id, ctx.room.name)


server = agents.AgentServer(
    ws_url=os.getenv("LIVEKIT_URL"),
    api_key=os.getenv("LIVEKIT_API_KEY"),
    api_secret=os.getenv("LIVEKIT_API_SECRET"),
)
server.rtc_session(entrypoint, agent_name="followup-voice-agent")


def start() -> None:
    """Run the LiveKit Agents worker process."""
    _required_env("LIVEKIT_URL")
    _required_env("LIVEKIT_API_KEY")
    _required_env("LIVEKIT_API_SECRET")
    _required_env("DEEPGRAM_API_KEY")
    _required_env("CARTESIA_API_KEY")
    _required_env("CARTESIA_VOICE_ID")
    agents.cli.run_app(server)
