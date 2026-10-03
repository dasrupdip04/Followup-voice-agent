from __future__ import annotations

import json
import os
import re
from typing import Any

from google import genai
from google.genai import types

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


class CallStrategyService:
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        self.client = genai.Client(api_key=self.api_key)

    @staticmethod
    def _parse_json_response(raw_text: str | Any) -> dict[str, Any]:
        if raw_text is None:
            raise ValueError("Gemini returned no JSON payload")

        text = str(raw_text).strip()
        if not text:
            raise ValueError("Gemini returned an empty strategy")

        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].lstrip()

        candidates: list[str] = []
        norm = re.sub(r"\s+", " ", text)
        candidates.append(norm)

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            candidates.append(text[start:end + 1])
            candidates.append(re.sub(r"\s+", " ", text[start:end + 1]))

        for candidate in candidates:
            stripped = candidate.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

        raise ValueError(f"Gemini returned malformed JSON: {text[:300]}")

    @staticmethod
    def _fallback_strategy(customer_context: dict[str, Any]) -> dict[str, Any]:
        customer = customer_context.get("customer") or {}
        loans = customer_context.get("active_loans") or []
        overdue = [loan for loan in loans if str(loan.get("status", "")).upper() == "OVERDUE"]
        main_loan = overdue[0] if overdue else (loans[0] if loans else {})
        customer_name = customer.get("full_name") or "customer"
        loan_ref = main_loan.get("loan_number") or "the active loan"
        amount = main_loan.get("outstanding_amount")
        issue = f"{loan_ref} is the main repayment concern" if main_loan else "Review the customer’s repayment status"
        if amount is not None:
            issue = f"{loan_ref} has an outstanding balance of {amount}"

        return {
            "objective": f"Follow up with {customer_name} on the active repayment discussion and secure a feasible commitment.",
            "priority_issue": issue,
            "customer_risk_context": "Customer has active loan obligations and may need a tailored repayment or callback plan.",
            "recommended_opening": f"Hello {customer_name}, this is a follow-up regarding your loan account and repayment plan.",
            "key_facts_to_mention": [
                f"Customer has {len(loans)} active loan(s)",
                f"Primary focus: {loan_ref}",
                "Use only facts from the customer's profile and loan records.",
            ],
            "questions_to_ask": [
                "Can you confirm the most feasible repayment date for the outstanding balance?",
                "Would you like to discuss a callback or revised repayment plan?",
            ],
            "possible_objections": [
                "Temporary cash flow constraints",
                "Payment processing or bank transfer issues",
                "Need to review documents or family approval",
            ],
            "recommended_response_style": "Professional, empathetic, and concise.",
            "payment_commitment_goal": "Secure a specific payment date or revised installment arrangement.",
            "escalation_conditions": [
                "Customer refuses to discuss repayment",
                "Customer is unreachable or non-responsive",
                "There is a dispute requiring a human team review",
            ],
            "topics_to_avoid": [
                "Incorrect promises or invented amounts",
                "Speculation about job or income status",
                "Unverified personal financial claims",
            ],
        }

    def generate_strategy(self, customer_context: dict[str, Any]) -> dict[str, Any]:
        prompt = json.dumps({
            "customer_context": customer_context,
            "task": "Generate a concise collections follow-up strategy using only supplied facts. Return JSON with structured keys only."
        }, default=str)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=(
                "You are a collections follow-up assistant for a banking loan team. "
                "Generate a compact, factual strategy for a customer conversation. "
                "Use only facts present in the supplied customer context. "
                "Do not invent amounts, dates, or promises. "
                "Output valid JSON with exactly these keys: "
                "objective, priority_issue, customer_risk_context, recommended_opening, key_facts_to_mention, "
                "questions_to_ask, possible_objections, recommended_response_style, payment_commitment_goal, "
                "escalation_conditions, topics_to_avoid. "
                "Values must be JSON primitives or arrays of strings. "
                f"Customer context: {prompt}"
            ),
            config=types.GenerateContentConfig(
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

        if not text or not str(text).strip():
            raise ValueError("Gemini returned an empty strategy")

        try:
            return self._parse_json_response(text)
        except ValueError:
            return self._fallback_strategy(customer_context)
