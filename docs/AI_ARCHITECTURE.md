# AI Architecture

## The one rule everything else follows

> The AI must never invent business data, and must never take a consequential action itself.

Concretely:

1. The AI has **no SQL or ORM access**. It can only call 14 named functions in
   `app/services/ai/tools.py` (`TOOL_REGISTRY`), each of which returns a small, already-computed
   JSON result built from the same analytics/forecasting/risk services the rest of the app uses.
   Adding a capability means adding a function here — never widening what the AI can query.
2. The AI can **never place an order**. `create_purchase_draft` is deliberately *not* a tool
   the AI can call from chat — a purchase order only comes into existence through
   `POST /api/ai/recommendations/{id}/approve`, which requires a human, is gated by
   `require_role(OWNER, MANAGER)`, and always creates the order in `DRAFT` status.
3. Every answer the AI gives is structured as **Answer / Evidence / Reasoning / Suggested
   action** (§24), and the Evidence is always the literal tool output — never paraphrased
   into something that could drift from the numbers.

## Provider-agnostic by design (§4, §22)

```
app/services/ai/
  provider.py       AIProvider (abstract) — NullProvider (deterministic fallback) and
                     AnthropicProvider (real model) both implement `next_step(...)`
  tools.py          TOOL_REGISTRY (14 functions) + TOOL_SPECS (their JSON-schema descriptions)
  orchestrator.py    chat(): runs the tool-calling loop and formats the final answer
```

- **No AI provider configured (`AI_PROVIDER=none`, the default):** `NullProvider` maps the
  question to relevant tools by keyword (e.g. "purchase"/"restock" → low-stock + supplier
  tools), calls them, and formats the results into prose. This is fully functional — every
  demo screenshot and the end-to-end test run in this mode — because the "intelligence" here
  is the *data pipeline*, not a language model.
- **`AI_PROVIDER=anthropic` + `AI_API_KEY` set:** `AnthropicProvider` calls the real Claude
  Messages API with the same `TOOL_SPECS`, lets the model decide which tools to call,
  executes them through the same `TOOL_REGISTRY`, and feeds the results back for a final
  answer. If the API call fails for any reason, `orchestrator.chat()` transparently falls
  back to the deterministic path rather than erroring out (see `orchestrator.py`'s "safety
  net").
- Swapping in OpenAI, Gemini, or any other vendor means adding one more `AIProvider`
  subclass — nothing in `tools.py`, the API routes, or the frontend changes.

The chat response always reports `used_live_model: bool` so the UI (and the person) can see
which mode produced an answer — `Settings → System status` and a badge on every chat message
both surface this. No API key is ever returned to the frontend.

## The recommendation pipeline (§25)

```
Products+Sales → forecast_product_demand() → risk_level in (HIGH, CRITICAL)?
                                                     │
                                           best available supplier
                                    (cheapest within 10% of lowest, tie-broken
                                     by reliability — not silently "cheapest wins")
                                                     │
                                     Recommendation(evidence=..., reasoning=...)
                                                     │
                                    human clicks Approve  ──────────────►  reject → done
                                                     │
                                     PurchaseOrder(status=DRAFT, source=ai_recommendation)
                                                     │
                                          audit.record(...) × 2
```

`app/services/recommendations.py::generate_procurement_recommendations` never recommends a
product that already has a pending recommendation (no duplicate spam), and never recommends
one when there isn't at least 7 days of sales history to forecast from — it says so via the
UI's "Nothing needs reordering right now (or there isn't enough sales history yet)" message
rather than guessing.

## Testing the AI layer honestly

`backend/tests/test_ai.py` doesn't just check that the assistant responds — it asserts:
- the assistant's answer contains the *exact* number a tool returned (not a rewritten one);
- an empty business gets "insufficient data," not an invented risk;
- `create_purchase_draft` is not in the tool registry an LLM could call;
- approving a recommendation creates a `DRAFT` PO and nothing more;
- rejecting creates no purchase order at all;
- a second approval attempt on the same recommendation is rejected (no double-spend).
