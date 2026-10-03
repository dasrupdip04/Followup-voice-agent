"""Tool layer for Gemini function calling."""

from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal
from typing import Any, Callable

from google.genai import types

from app.tools.call_tools import (
    record_conversation_turn,
    record_customer_response,
    save_call_event,
    update_call_outcome,
)
from app.tools.customer_tools import (
    get_customer_call_history,
    get_customer_context,
    get_customer_loans,
    get_customer_profile,
    get_full_customer_context,
    get_loan_details,
    get_payment_history,
)
from app.tools.payment_tools import record_payment_commitment

CUSTOMER_SCOPED_TOOL_NAMES: set[str] = {
    "get_customer_profile",
    "get_customer_loans",
    "get_customer_call_history",
    "get_customer_context",
    "get_full_customer_context",
}

LOAN_SCOPED_TOOL_NAMES: set[str] = {
    "get_loan_details",
    "get_payment_history",
}

ALLOWED_TOOL_NAMES: set[str] = (
    CUSTOMER_SCOPED_TOOL_NAMES
    | LOAN_SCOPED_TOOL_NAMES
    | {
        "record_payment_commitment",
        "record_conversation_turn",
        "record_customer_response",
        "update_call_outcome",
        "save_call_event",
    }
)

TOOL_DESCRIPTIONS: dict[str, str] = {
    "get_customer_profile": "Return the profile of the active customer in the current conversation. This tool uses the trusted request/customer context automatically; do not ask Gemini to provide customer_id.",
    "get_customer_loans": "Return all loans for the active customer in the current conversation. Use this only when the user asks about their loans. The backend injects the trusted current customer automatically; do not pass customer_id.",
    "get_full_customer_context": "Return the complete customer context in one backend query: profile, active loans, payment history, and previous calls. Use this instead of separate customer and loan read tools whenever the full context is needed.",
    "get_loan_details": "Return details for a single loan using loan_id. Only call this when the user asks about one specific loan. The loan_id must belong to the current trusted customer; never query another customer's loan.",
    "get_payment_history": "Return payment history for a specific loan using loan_id. Only use this when the user asks about payments. The loan_id must belong to the current trusted customer; do not access another customer's loan.",
    "get_customer_call_history": "Return recent call history for the active customer in the current conversation. The backend injects the trusted current customer automatically; do not pass customer_id.",
    "get_customer_context": "Return the full customer context for the active customer: profile, loans, and recent payments. This tool uses the trusted current customer automatically; do not pass customer_id.",
    "record_payment_commitment": "Record a customer's promised payment against a loan that belongs to the current customer. Validate the loan belongs to the current customer before writing.",
    "record_conversation_turn": "Persist a conversation turn for the active call record. Only use this when a turn needs to be recorded in the database.",
    "record_customer_response": "Persist a structured customer response summary for the active call. Only call when the customer gave a response that should be stored.",
    "update_call_outcome": "Update the call outcome for the active call. Use only when the call status or resolution needs to be persisted.",
    "save_call_event": "Persist a call event for the active call with structured metadata. Use this only when an event needs to be recorded.",
}


def _coerce_value(name: str, value: Any) -> Any:
    if value is None:
        return None
    if name.endswith("_id"):
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return value
            if cleaned.lower() in {"current_customer", "current customer", "customer", "this_customer"}:
                return value
            try:
                return int(cleaned)
            except ValueError:
                return value
        return int(value)
    if name in {"amount", "principal_amount", "outstanding_amount", "interest_rate", "emi_amount", "promised_amount"}:
        return Decimal(str(value))
    if name in {"latency_ms", "duration_seconds", "tool_calls", "tool_failures", "total_turns", "user_turns", "agent_turns"}:
        return int(value)
    if name == "commitment_date" and isinstance(value, str):
        return date.fromisoformat(value)
    if name == "metadata" and isinstance(value, dict):
        return value
    return value


def _normalize_tool_arguments(function_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        return {}

    normalized = {key: _coerce_value(key, value) for key, value in arguments.items()}
    if function_name in CUSTOMER_SCOPED_TOOL_NAMES:
        normalized.pop("customer_id", None)
        normalized.pop("current_customer", None)
    return normalized


def _schema_from_callable(fn: Callable[..., Any], *, tool_name: str) -> types.Schema:
    signature = inspect.signature(fn)
    props: dict[str, types.Schema] = {}
    required: list[str] = []

    for param_name, param in signature.parameters.items():
        if param_name == "db" or param_name.startswith("_"):
            continue
        if tool_name in CUSTOMER_SCOPED_TOOL_NAMES and param_name == "customer_id":
            continue
        if tool_name in LOAN_SCOPED_TOOL_NAMES and param_name == "customer_id":
            continue
        if param.default is inspect._empty:
            required.append(param_name)

        schema_type = types.Type.STRING
        if param.annotation is inspect._empty:
            annotation = str
        else:
            annotation = param.annotation

        origin = getattr(annotation, '__origin__', None)
        if origin is list:
            schema_type = types.Type.ARRAY
        elif annotation in (int, float):
            schema_type = types.Type.NUMBER if annotation is float else types.Type.INTEGER
        elif annotation is bool:
            schema_type = types.Type.BOOLEAN
        elif annotation is dict:
            schema_type = types.Type.OBJECT
        elif annotation is str:
            schema_type = types.Type.STRING

        if schema_type == types.Type.ARRAY:
            props[param_name] = types.Schema(type=schema_type, items=types.Schema(type=types.Type.STRING))
        else:
            props[param_name] = types.Schema(type=schema_type)

    return types.Schema(
        type=types.Type.OBJECT,
        properties=props,
        required=required,
    )


def get_tool_registry() -> list[types.FunctionDeclaration]:
    functions: dict[str, Callable[..., Any]] = {
        "get_customer_profile": get_customer_profile,
        "get_customer_loans": get_customer_loans,
        "get_full_customer_context": get_full_customer_context,
        "get_loan_details": get_loan_details,
        "get_payment_history": get_payment_history,
        "get_customer_call_history": get_customer_call_history,
        "get_customer_context": get_customer_context,
        "record_payment_commitment": record_payment_commitment,
        "record_conversation_turn": record_conversation_turn,
        "record_customer_response": record_customer_response,
        "update_call_outcome": update_call_outcome,
        "save_call_event": save_call_event,
    }

    declarations: list[types.FunctionDeclaration] = []
    for name, fn in functions.items():
        declarations.append(
            types.FunctionDeclaration(
                name=name,
                description=TOOL_DESCRIPTIONS.get(name, fn.__doc__ or f"Execute {name}").strip(),
                parameters=_schema_from_callable(fn, tool_name=name),
            )
        )
    return declarations


def get_tool_function(name: str) -> Callable[..., Any]:
    if name not in ALLOWED_TOOL_NAMES:
        raise ValueError(f"Tool '{name}' is not allowed")

    registry = {
        "get_customer_profile": get_customer_profile,
        "get_customer_loans": get_customer_loans,
        "get_full_customer_context": get_full_customer_context,
        "get_loan_details": get_loan_details,
        "get_payment_history": get_payment_history,
        "get_customer_call_history": get_customer_call_history,
        "get_customer_context": get_customer_context,
        "record_payment_commitment": record_payment_commitment,
        "record_conversation_turn": record_conversation_turn,
        "record_customer_response": record_customer_response,
        "update_call_outcome": update_call_outcome,
        "save_call_event": save_call_event,
    }
    return registry[name]
