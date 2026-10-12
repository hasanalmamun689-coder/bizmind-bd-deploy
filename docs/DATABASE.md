# Database

PostgreSQL, accessed through SQLAlchemy 2.0 (typed `Mapped[...]` models) and migrated with
Alembic. Every table uses a UUID primary key and `created_at`/`updated_at` timestamps
(`app/models/mixins.py`).

## Entities

| Table | Notes |
|---|---|
| `businesses` | Tenant. Every business-scoped table has a `business_id` FK to this. |
| `users` | Also serves as the spec's `employees` entity — see "Simplifications" below. |
| `categories`, `products` | `products.status` (healthy/low_stock/critical/out_of_stock/overstock) is derived by `Product.recompute_status()` whenever stock changes — never set directly by client input. |
| `customers` | Segment (new/regular/high-value/inactive) is computed on read in `app/services/analytics.py`, not stored — it's a live rule, not a stored label (§14). |
| `sales`, `sale_items` | A sale's `total_amount`/`total_cost` are the sum of its items, computed at creation time from the product's *current* prices (a later price change never rewrites historical sales). |
| `inventory_transactions` | Append-only ledger. Every stock change (sale, stock-in, stock-out, manual adjustment, sale cancellation) writes exactly one row here — this is the audit trail behind `current_stock`. |
| `suppliers`, `supplier_products` | `supplier_products` is the price/MOQ a specific supplier quotes for a specific product. |
| `supplier_price_history` | Append-only log of every price a supplier has quoted; only a real value change is logged. This is what lets the risk engine detect a genuine price increase rather than guessing from one snapshot. |
| `purchase_orders`, `purchase_order_items` | `status` follows a strict state machine (draft → pending_approval → approved → ordered → delivered → completed, or → cancelled at most steps) enforced server-side in `app/api/v1/procurement.py::ALLOWED_TRANSITIONS`. `source` is `manual` or `ai_recommendation`. |
| `expenses`, `payments` | `payments` is a light generic ledger (`related_type` + `related_id`) for sale/PO/expense payments; not deeply used yet in the UI. |
| `forecasts` | One row per forecast *run*, kept as history (not overwritten), so forecast accuracy can be reviewed later. |
| `alerts` | Persisted notifications (low stock, etc.) with severity/status, separate from... |
| ...live risk detection | `app/services/risk.py` computes business risks (sales decline, expense spikes, profit decline, supplier reliability/price increases, dead stock, overstock, rapid depletion) on demand — these are not stored rows, since they're a function of current data and would go stale instantly. |
| `recommendations` | The AI recommendation pipeline's output. `evidence` (JSON) and `reasoning` are populated only from real tool results. |
| `ai_conversations`, `ai_messages` | Chat history; `ai_messages.evidence` stores exactly what the assistant showed the user. |
| `agent_runs` | One row per AI orchestration invocation (chat or recommendation generation), for traceability — not just chat. |
| `audit_logs` | Every consequential action, written through the single `app/services/audit.py::record()` helper. |

## Simplifications (allowed by §6: "the implementation may simplify the schema... but
relationships must remain logically correct")

- **No separate `employees` table.** At SME scale, every login-capable person *is* an
  employee; a 1:1 `employees` table would just duplicate `users` columns. `User.job_title`
  and `User.role` carry what the spec's `employees` entity needs.
- **Customer segments are computed, not stored** — see above; this also matches §14's
  caution against presenting a simplistic segmentation as a fixed, authoritative label.
- **Risks are computed, not stored** — `alerts` are persisted (they need read/unread state);
  business risks (§21) are recomputed live from current data every time they're requested.

## Migrations

```
0001_initial_schema.py                    all tables
0002_price_history_and_indexes.py         supplier_price_history + business_id/FK indexes
0003_unique_product_sku_per_business.py   UNIQUE(business_id, sku)
```

Generate a new one after changing `app/models/`:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```
