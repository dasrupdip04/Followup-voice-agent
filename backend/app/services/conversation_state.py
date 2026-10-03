from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ConversationState:
    customer_id: int
    call_id: int | None = None
    customer_context: dict[str, Any] = field(default_factory=dict)
    call_strategy: dict[str, Any] | None = None
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    current_objective: str | None = None
    collected_information: dict[str, Any] = field(default_factory=dict)
    commitments: list[dict[str, Any]] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    next_action: str | None = None
    turn_count: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class ConversationStateStore:
    _instance: "ConversationStateStore | None" = None

    def __new__(cls) -> "ConversationStateStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._by_call_id: dict[int, ConversationState] = {}
            cls._instance._by_customer_id: dict[int, ConversationState] = {}
        return cls._instance

    def get_by_call_id(self, call_id: int) -> ConversationState | None:
        return self._by_call_id.get(call_id)

    def get_by_customer_id(self, customer_id: int) -> ConversationState | None:
        return self._by_customer_id.get(customer_id)

    def store(self, state: ConversationState) -> None:
        if state.call_id is not None:
            self._by_call_id[state.call_id] = state
        self._by_customer_id[state.customer_id] = state

    def clear_call(self, call_id: int | None) -> None:
        if call_id is None:
            return
        state = self._by_call_id.pop(call_id, None)
        if state is not None:
            self._by_customer_id.pop(state.customer_id, None)

    def get_or_create(self, *, customer_id: int, call_id: int | None = None) -> ConversationState:
        state = self._by_customer_id.get(customer_id)
        if state is None:
            state = ConversationState(customer_id=customer_id, call_id=call_id)
            self.store(state)
        elif call_id is not None:
            state.call_id = call_id
            self._by_call_id[call_id] = state
        return state
