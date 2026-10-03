"""LiveKitAgent glue: initializes providers and manages simple session lifecycle.

This module intentionally avoids making live calls during import and provides
lightweight smoke-test helpers that validate configuration and imports.
"""
import os
from typing import Optional
from app.livekit_agent.session import LiveSession
from app.livekit_agent.prompts import OPENING_PROMPT, TURN_PROMPT
from app.services.gemini_service import GeminiService


class LiveKitAgent:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        # prefer env vars for runtime configuration
        self.livekit_url = self.config.get("LIVEKIT_URL") or os.getenv("LIVEKIT_URL")
        self.livekit_api_key = self.config.get("LIVEKIT_API_KEY") or os.getenv("LIVEKIT_API_KEY")
        self.livekit_api_secret = self.config.get("LIVEKIT_API_SECRET") or os.getenv("LIVEKIT_API_SECRET")
        self.deepgram_key = self.config.get("DEEPGRAM_API_KEY") or os.getenv("DEEPGRAM_API_KEY")
        self.deepgram_model = self.config.get("DEEPGRAM_MODEL") or os.getenv("DEEPGRAM_MODEL")
        self.cartesia_key = self.config.get("CARTESIA_API_KEY") or os.getenv("CARTESIA_API_KEY")
        self.cartesia_model = self.config.get("CARTESIA_MODEL") or os.getenv("CARTESIA_MODEL")
        self.cartesia_voice_id = self.config.get("CARTESIA_VOICE_ID") or os.getenv("CARTESIA_VOICE_ID")
        self.gemini = GeminiService()

        # provider placeholders — initialized lazily to avoid noisy network ops
        self.livekit_client = None
        self.deepgram_plugin = None
        self.cartesia_plugin = None

    def init_providers(self):
        """Attempt to import and initialize provider SDKs/plugins.

        This method intentionally does not join rooms or open sockets. It
        only validates imports and basic configuration so a smoke test can
        assert readiness without network operations.
        """
        errors = {}

        # LiveKit agents
        try:
            import livekit_agents  # type: ignore

            # keep the module reference; do not start network IO here
            self.livekit_client = livekit_agents
        except Exception as e:  # pragma: no cover - best-effort import
            errors["livekit_agents"] = str(e)

        # Deepgram plugin
        try:
            import livekit_plugins_deepgram as _dg  # type: ignore

            self.deepgram_plugin = _dg
        except Exception as e:  # pragma: no cover
            errors["deepgram_plugin"] = str(e)

        # Cartesia plugin
        try:
            import livekit_plugins_cartesia as _ct  # type: ignore

            self.cartesia_plugin = _ct
        except Exception as e:  # pragma: no cover
            errors["cartesia_plugin"] = str(e)

        return errors

    def smoke_test(self) -> dict:
        """Run an import/config smoke test for the three providers and Gemini.

        Returns a dict with the status of each provider and any import errors.
        """
        result = {"gemini": True, "gemini_model": getattr(self.gemini, "model_name", None)}
        imports = self.init_providers()
        result.update({"imports": imports})

        # check basic config presence
        result["livekit_configured"] = bool(self.livekit_url and self.livekit_api_key and self.livekit_api_secret)
        result["deepgram_configured"] = bool(self.deepgram_key and self.deepgram_model)
        result["cartesia_configured"] = bool(self.cartesia_key and self.cartesia_model and self.cartesia_voice_id)

        return result

    def create_session(self, room_sid: str, customer_id: int) -> LiveSession:
        """Create a new LiveSession placeholder. Call lifecycle start should be
        invoked by the caller (LiveKit event handler) using the Phase 6 service.
        """
        session = LiveSession(room_sid=room_sid, customer_id=customer_id)
        # Attach a compact opening strategy placeholder — real generation should
        # use existing CallStrategyService once the call is started.
        session.strategy = {"objective": "Opening: introduce, confirm identity, discuss payment options"}
        return session

    # Room/join helpers are intentionally not implemented here because the
    # concrete LiveKit Agents API and runtime details vary; implementors can
    # use `self.livekit_client` (if available) to create an agent that joins
    # a room and wires Deepgram + Cartesia plugin policies.
