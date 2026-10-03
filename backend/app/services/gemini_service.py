import os
from typing import Any

from google import genai
from google.genai import types

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

    def health_check(self) -> bool:
        return bool(self.api_key)
