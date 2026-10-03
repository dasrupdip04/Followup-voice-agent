from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LiveSession:
    """In-memory session state for a LiveKit call.

    This intentionally mirrors the Phase 6 conversation state but is scoped
    to the LiveKit session lifecycle.
    """
    room_sid: str
    customer_id: int
    call_id: Optional[int] = None
    strategy: Optional[Dict[str, Any]] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    last_activity_at: Optional[str] = None

    def append_user_turn(self, text: str, timestamp: Optional[str] = None):
        self.history.append({"role": "user", "text": text, "ts": timestamp})

    def append_agent_turn(self, text: str, timestamp: Optional[str] = None):
        self.history.append({"role": "agent", "text": text, "ts": timestamp})
