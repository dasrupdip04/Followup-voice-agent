"""LiveKit runner that joins rooms, wires Deepgram and Cartesia, and
connects to Gemini via existing services.

This runner uses dynamic imports and defensive coding so tests can run
without the provider SDKs present. When the SDKs are available it will
attempt to create an agent and join LiveKit rooms.

Network operations are performed only by `start()` when the SDKs are
available and environment variables are configured.
"""
import os
import time
import logging
from typing import Optional

from app.livekit_agent.agent import LiveKitAgent
from app.livekit_agent.tools import start_call_for_session, end_call_for_session, append_turn
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class LiveKitRunner:
    def __init__(self, config: Optional[dict] = None):
        self.agent = LiveKitAgent(config=config)
        self.gemini = GeminiService()
        self._sdk_ready = False
        self._agent_obj = None

    def init_sdks(self):
        """Import and initialize SDKs/plugins. Returns dict of errors if any."""
        errors = self.agent.init_providers()
        # consider SDKs ready if imports succeeded
        self._sdk_ready = not bool(errors)
        return errors

    def start(self):
        """Start a basic agent loop: connect to LiveKit if available.

        This method will block and run until stopped or an error occurs. It
        is intentionally simple: production deployments should run this in
        a supervised process manager.
        """
        errors = self.init_sdks()
        if errors:
            logger.info("SDK import issues: %s", errors)
        if not self._sdk_ready:
            logger.warning("SDKs not available, runner will not join LiveKit rooms.")
            return {"status": "skipped", "errors": errors}

        # If livekit_agents is available, attempt to create an agent and join
        try:
            import livekit_agents as lka  # type: ignore

            # Create an agent builder and attach plugins if supported.
            builder = getattr(lka, "LiveAgent", None) or getattr(lka, "Agent", None) or None
            if builder is None:
                # fallback to exposing the module for advanced callers
                self._agent_obj = lka
                logger.info("livekit_agents module loaded but Agent class not found; manual wiring required.")
                return {"status": "loaded", "note": "manual wiring required"}

            # build agent with configured credentials
            livekit_url = os.getenv("LIVEKIT_URL")
            api_key = os.getenv("LIVEKIT_API_KEY")
            api_secret = os.getenv("LIVEKIT_API_SECRET")

            agent_kwargs = {"url": livekit_url, "api_key": api_key, "api_secret": api_secret}

            # instantiate the agent
            self._agent_obj = builder(**agent_kwargs)
            logger.info("Agent instantiated")

            # In production, attach plugin wiring: Deepgram, Cartesia
            # Many livekit_agents versions provide .use_plugin or similar hooks
            try:
                if hasattr(self._agent_obj, "use_plugin"):
                    # attach plugins by name if available
                    if hasattr(self.agent, "deepgram_plugin") and self.agent.deepgram_plugin:
                        self._agent_obj.use_plugin(self.agent.deepgram_plugin)
                    if hasattr(self.agent, "cartesia_plugin") and self.agent.cartesia_plugin:
                        self._agent_obj.use_plugin(self.agent.cartesia_plugin)
            except Exception:
                logger.exception("Failed to attach plugins; continuing without plugin auto-attach")

            # start the agent run loop — concrete API differs by livekit_agents
            if hasattr(self._agent_obj, "run"):
                logger.info("Starting agent run loop (this may block)")
                self._agent_obj.run()
            else:
                logger.info("Agent created; no run() entrypoint found — manual run required")

            return {"status": "running"}

        except Exception as exc:
            logger.exception("Failed to start LiveKit runner: %s", exc)
            return {"status": "error", "error": str(exc)}

    # Helper methods for integrating with call lifecycle and Gemini
    def handle_deepgram_final_transcript(self, session_room: str, customer_id: int, transcript: str, ts: Optional[float] = None):
        """Called when Deepgram emits a final transcript/turn.

        This implements the preferred flow: one Gemini call per user turn.
        """
        # create or find call via Phase 6 lifecycle (import at runtime to
        # allow tests to monkeypatch the tools module)
        from app.livekit_agent import tools as _tools

        call_info = _tools.start_call_for_session(customer_id=customer_id)
        call_id = call_info.get("call_id")

        # record user turn (in DB via wrapper)
        _tools.append_turn(call_id=call_id, role="user", text=transcript)

        # ONE Gemini interaction: include last few turns + strategy if available
        prompt = transcript
        start_time = time.time()
        response = self.gemini.generate_reply(prompt_text=prompt)
        gemini_latency = time.time() - start_time

        # record agent turn and persist
        reply_text = response.get("text") if isinstance(response, dict) else str(response)
        _tools.append_turn(call_id=call_id, role="agent", text=reply_text)

        # send to TTS via Cartesia plugin — actual publishing is handled by LiveKit runtime
        # we simply return the reply and timing metrics
        return {"reply": reply_text, "gemini_latency": gemini_latency}
