"""
section 4/22: "Create a provider-agnostic AI service abstraction. Do not
tightly couple the entire application to one AI provider."

`AIProvider` is the seam. `AnthropicProvider` is a real implementation
(used when AI_PROVIDER=anthropic and AI_API_KEY is set); `NullProvider` is a
deterministic, keyword-based fallback used whenever no key is configured, so
the AI assistant remains fully functional (using only real business data)
without any external dependency. Swapping in an OpenAI/Gemini provider means
adding one more class here — nothing else in the codebase changes.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderResponse:
    tool_calls: list[ToolCall]
    final_text: str | None  # set only once the provider is done calling tools


class AIProvider(ABC):
    @abstractmethod
    def next_step(
        self,
        system_prompt: str,
        conversation: list[dict[str, str]],
        tool_specs: list[dict],
        tool_results: list[dict],
    ) -> ProviderResponse:
        """
        Given the conversation so far and any tool results gathered in this
        turn, decide whether to call more tools or return a final answer.
        """
        raise NotImplementedError


class NullProvider(AIProvider):
    """
    Deterministic fallback used when no AI_API_KEY is configured. It maps
    the user's question to a small set of relevant tools via keyword
    matching, then formats the tool results into a plain-language answer.
    It NEVER fabricates a number that didn't come from a tool result.
    """

    KEYWORD_TOOL_MAP = [
        (("purchase", "buy", "restock", "reorder", "should i order"), ["get_low_stock_products", "get_supplier_performance"]),
        (("profit", "margin", "why did my profit"), ["calculate_profit", "get_expense_breakdown"]),
        (("risk", "wrong", "concern", "problem"), ["get_business_risks"]),
        (("stock", "inventory", "run out", "stockout"), ["get_inventory_status", "get_low_stock_products"]),
        (("sell", "selling", "sales", "revenue", "best seller", "top product"), ["get_sales_summary", "get_product_sales"]),
        (("supplier", "vendor"), ["get_supplier_performance", "get_supplier_prices"]),
        (("expense", "cost", "spending"), ["get_expense_breakdown"]),
        (("customer",), ["get_customer_summary"]),
    ]

    def next_step(self, system_prompt, conversation, tool_specs, tool_results):
        if tool_results:
            # Second pass: we already have data, produce the final answer.
            return ProviderResponse(tool_calls=[], final_text=None)

        last_user_message = next(
            (m["content"] for m in reversed(conversation) if m["role"] == "user"), ""
        ).lower()

        matched: list[str] = []
        for keywords, tools in self.KEYWORD_TOOL_MAP:
            if any(k in last_user_message for k in keywords):
                matched.extend(t for t in tools if t not in matched)

        if not matched:
            matched = ["get_sales_summary", "get_business_risks"]

        return ProviderResponse(tool_calls=[ToolCall(name=t) for t in matched], final_text=None)


class AnthropicProvider(AIProvider):
    """Real LLM call via the Anthropic Messages API, used when configured."""

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model or "claude-sonnet-4-6"

    def _anthropic_tools(self, tool_specs: list[dict]) -> list[dict]:
        tools = []
        for spec in tool_specs:
            properties = {
                name: {"type": "string", "description": desc}
                for name, desc in spec["parameters"].items()
            }
            tools.append(
                {
                    "name": spec["name"],
                    "description": spec["description"],
                    "input_schema": {"type": "object", "properties": properties},
                }
            )
        return tools

    def next_step(self, system_prompt, conversation, tool_specs, tool_results):
        messages = [{"role": m["role"], "content": m["content"]} for m in conversation]
        if tool_results:
            messages.append(
                {
                    "role": "user",
                    "content": f"Tool results (JSON): {json.dumps(tool_results)}. "
                    "Using only this data, give the final answer.",
                }
            )

        try:
            resp = httpx.post(
                self.API_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 1024,
                    "system": system_prompt,
                    "messages": messages,
                    "tools": self._anthropic_tools(tool_specs) if not tool_results else [],
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            # Network/API failure: degrade gracefully rather than crash the
            # request (section 36 — no raw exceptions surfaced to the user).
            return ProviderResponse(tool_calls=[], final_text=None)

        tool_calls = []
        text_parts = []
        for block in data.get("content", []):
            if block.get("type") == "tool_use":
                tool_calls.append(ToolCall(name=block["name"], arguments=block.get("input", {})))
            elif block.get("type") == "text":
                text_parts.append(block["text"])

        if tool_calls:
            return ProviderResponse(tool_calls=tool_calls, final_text=None)
        return ProviderResponse(tool_calls=[], final_text="\n".join(text_parts) or None)


def get_provider() -> AIProvider | None:
    if settings.AI_PROVIDER == "anthropic" and settings.AI_API_KEY:
        return AnthropicProvider(settings.AI_API_KEY, settings.AI_MODEL)
    return None
