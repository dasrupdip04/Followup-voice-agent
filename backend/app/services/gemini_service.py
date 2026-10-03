import json
import os
from typing import Any

from google import genai
from google.genai import types
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.tools import ALLOWED_TOOL_NAMES, _normalize_tool_arguments, get_tool_function, get_tool_registry

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


class GeminiConfigError(RuntimeError):
    pass


class GeminiService:
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise GeminiConfigError("GEMINI_API_KEY is not configured")

        self.model_name = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        self.client = genai.Client(api_key=self.api_key)

    def generate_agent_response(
        self,
        *,
        system_instructions: str,
        conversation_history: list[dict[str, str]] | None = None,
        current_message: str,
        customer_context: dict[str, Any] | None = None,
    ) -> str:
        if not current_message or not current_message.strip():
            raise ValueError("current_message must not be empty")

        history = conversation_history or []

        prompt_parts: list[str] = []
        prompt_parts.append(f"System instructions:\n{system_instructions}\n")

        if customer_context:
            prompt_parts.append("Customer context:\n")
            prompt_parts.append(str(customer_context))
            prompt_parts.append("\n")

        if history:
            prompt_parts.append("Conversation history:\n")
            for turn in history:
                speaker = turn.get("speaker", "unknown")
                text = turn.get("text", "")
                prompt_parts.append(f"{speaker}: {text}\n")

        prompt_parts.append("Current user message:\n")
        prompt_parts.append(current_message)

        combined_prompt = "".join(prompt_parts)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=combined_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    top_p=0.9,
                    max_output_tokens=512,
                ),
            )
        except Exception as exc:
            raise RuntimeError(f"Gemini API request failed: {exc}") from exc

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

        if not text or not str(text).strip():
            raise ValueError("Gemini response is empty or malformed")

        return str(text).strip()

    def _resolve_trusted_customer_id(self, customer_context: dict[str, Any] | None, request_customer_id: int | None) -> int | None:
        if request_customer_id is not None:
            return int(request_customer_id)
        if customer_context and isinstance(customer_context, dict):
            for key in ("customer_id", "id"):
                value = customer_context.get(key)
                if value is not None:
                    return int(value)
        return None

    def _prepare_tool_payload(self, tool_name: str, payload: dict[str, Any], trusted_customer_id: int | None) -> dict[str, Any]:
        cleaned = _normalize_tool_arguments(tool_name, payload or {})

        if tool_name in {"get_customer_profile", "get_customer_loans", "get_customer_call_history", "get_customer_context"}:
            cleaned["_trusted_customer_id"] = trusted_customer_id
            cleaned.pop("customer_id", None)
        elif tool_name in {"get_loan_details", "get_payment_history"}:
            cleaned["_trusted_customer_id"] = trusted_customer_id
            cleaned.pop("customer_id", None)
        return cleaned

    def execute_tool_call(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        db: Session | None = None,
        trusted_customer_id: int | None = None,
    ) -> dict[str, Any]:
        if tool_name not in ALLOWED_TOOL_NAMES:
            raise ValueError(f"Tool '{tool_name}' is not allowed")

        fn = get_tool_function(tool_name)
        session = db or SessionLocal()
        try:
            payload = self._prepare_tool_payload(tool_name, arguments or {}, trusted_customer_id)
            print(f"[tool-call] name={tool_name} args={payload}")
            result = fn(session, **payload)
            return {"tool": tool_name, "success": True, "result": result}
        finally:
            if db is None:
                session.close()

    def process_with_tools(
        self,
        *,
        system_instructions: str,
        conversation_history: list[dict[str, str]] | None = None,
        current_message: str,
        customer_context: dict[str, Any] | None = None,
        max_tool_rounds: int = 3,
        db: Session | None = None,
        trusted_customer_id: int | None = None,
    ) -> dict[str, Any]:
        if not current_message or not current_message.strip():
            raise ValueError("current_message must not be empty")

        resolved_customer_id = self._resolve_trusted_customer_id(customer_context, trusted_customer_id)
        history = conversation_history or []
        tool_results: list[dict[str, Any]] = []
        round_count = 0

        prompt_parts: list[str] = []
        prompt_parts.append(f"System instructions:\n{system_instructions}\n")
        if customer_context:
            prompt_parts.append("Customer context:\n")
            prompt_parts.append(str(customer_context))
            prompt_parts.append("\n")
        if resolved_customer_id is not None:
            prompt_parts.append(f"Current customer context (trusted): customer_id={resolved_customer_id}\n")
        if history:
            prompt_parts.append("Conversation history:\n")
            for turn in history:
                speaker = turn.get("speaker", "unknown")
                text = turn.get("text", "")
                prompt_parts.append(f"{speaker}: {text}\n")
        prompt_parts.append("Current user message:\n")
        prompt_parts.append(current_message)
        prompt = "".join(prompt_parts)

        while round_count < max_tool_rounds:
            round_count += 1
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        top_p=0.9,
                        max_output_tokens=512,
                        tools=[types.Tool(function_declarations=get_tool_registry())],
                        tool_config=types.ToolConfig(
                            function_calling_config=types.FunctionCallingConfig(
                                mode=types.FunctionCallingConfigMode.AUTO,
                            )
                        ),
                    ),
                )
            except Exception as exc:
                raise RuntimeError(f"Gemini API request failed: {exc}") from exc

            function_calls = []
            if getattr(response, "candidates", None):
                for candidate in response.candidates:
                    if getattr(candidate, "content", None) and getattr(candidate.content, "parts", None):
                        for part in candidate.content.parts:
                            if getattr(part, "function_call", None):
                                function_calls.append(part.function_call)

            if not function_calls:
                final_text = getattr(response, "text", None)
                if final_text is None and getattr(response, "candidates", None):
                    candidates = response.candidates
                    if candidates:
                        first = candidates[0]
                        if getattr(first, "content", None) and hasattr(first.content, "parts"):
                            assembled = []
                            for part in first.content.parts:
                                if hasattr(part, "text") and part.text:
                                    assembled.append(part.text)
                            final_text = "".join(assembled)
                if not final_text or not str(final_text).strip():
                    raise ValueError("Gemini response is empty or malformed")
                return {
                    "response": str(final_text).strip(),
                    "tool_calls": tool_results,
                    "tool_rounds": round_count,
                    "model": self.model_name,
                    "status": "ok",
                }

            for call in function_calls:
                tool_name = getattr(call, "name", None)
                tool_args = getattr(call, "args", None) or {}
                if not tool_name:
                    continue
                if tool_name not in ALLOWED_TOOL_NAMES:
                    raise ValueError(f"Tool '{tool_name}' is not allowed")

                tool_result = self.execute_tool_call(
                    tool_name=tool_name,
                    arguments=_normalize_tool_arguments(tool_name, dict(tool_args)),
                    db=db,
                    trusted_customer_id=resolved_customer_id,
                )
                tool_results.append(tool_result)
                prompt += f"\nTool call: {tool_name}\nArguments: {json.dumps(tool_args, default=str)}\nTool result: {json.dumps(tool_result, default=str)}\n"

        raise RuntimeError("Gemini tool call loop exceeded max_tool_rounds")

    def health_check(self) -> bool:
        return bool(self.api_key)
