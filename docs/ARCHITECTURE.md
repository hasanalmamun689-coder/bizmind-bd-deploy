# Architecture

## Overview

```
DATA → INSIGHT → PREDICTION → RECOMMENDATION → HUMAN APPROVAL → ACTION
```

```
frontend/  Next.js (App Router) — talks to the backend only over HTTP/JSON
backend/   FastAPI — single deployable service (see "Why one backend service" below)
  app/
    api/v1/        one router per domain (auth, products, sales, inventory, ...)
    models/        SQLAlchemy ORM models (source of truth for the schema)
    schemas/       Pydantic request/response models
    services/       business logic — analytics, forecasting, risk detection, health score,
                    inventory ledger, audit logging, AI orchestration + tools + provider
    auth/           JWT decoding + require_role() RBAC dependency
    core/           config (env vars), security (hashing/JWT), clock (tz-aware "now")
    db/             SQLAlchemy engine/session
  alembic/          schema migrations
  tests/            pytest suite (55+ tests) against a real Postgres test database
database/seed/      realistic demo-data generator (Bangladeshi SME, BDT)
tests/e2e/          Playwright browser test of the full MVP journey
docs/               this file, API.md, DATABASE.md, AI_ARCHITECTURE.md, SETUP.md, DEPLOYMENT.md
```

## Why one backend service, not `backend/` + separate `ai-service/`

The master spec's reference layout lists `ai-service/` as a sibling of `backend/`. For an
MVP at this scale, splitting the AI layer into its own deployable service would add a
network hop, a second deployment, and duplicated auth/DB access for no real benefit — the
spec itself says (§42) that "a controlled AI orchestration/service layer is sufficient" for
MVP and warns against unnecessary multi-service complexity. The AI code still lives in its
own clearly-bounded module (`app/services/ai/`) with a closed tool interface
(`app/services/ai/tools.py`), so splitting it into a separate process later — if load or
team boundaries ever require it — is a matter of moving that module and adding an HTTP
shim, not a redesign.

## Multi-tenancy

Every business-scoped table has a `business_id` foreign key to `businesses`. Every query in
every router filters by `current_user.business_id` — there is no cross-tenant read path.
`tests/test_rbac_and_tenancy.py::test_tenant_isolation` asserts this directly (a second
business gets 404s and empty lists, never another business's data).

## RBAC

Two roles: `owner` and `manager` (§3). Enforcement is server-side only —
`Depends(require_role(UserRole.OWNER))` (or `OWNER, MANAGER`) gates every sensitive route
(employee management, audit logs, settings, expense deletion, purchase-order approval).
The frontend also hides owner-only nav items for managers, but that's a UX nicety; the API
is what actually blocks the request (`tests/test_rbac_and_tenancy.py`).

## Data consistency (§47)

A sale is the clearest example of the "modules must not be isolated" principle: creating a
sale (`POST /api/sales`) — in one DB transaction — saves the sale, saves each sale item,
reduces stock through the shared inventory ledger (`app/services/inventory.py`), writes an
inventory transaction, recomputes the product's status, and raises a low-stock alert the
moment the status crosses a threshold. Forecasting, risk detection and the AI tools all read
from that same ledger, so nothing needs to be told separately that a sale happened.

## AI safety boundary

See [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) for the full design. In one sentence: the AI
can only call 14 named, read-only functions that return already-computed business data, and
the only way an AI recommendation can affect the database is through a human clicking
"Approve," which creates a purchase order in `DRAFT` status — never `ordered` or beyond.

## What's deferred

- **Native Android app** (§40) — explicitly out of MVP scope per the spec; the API is
  already a clean JSON contract a mobile client could consume unchanged.
- **Multi-agent architecture** (§42) — a single orchestration layer is used, as recommended
  for MVP; `AgentRun` records already give every invocation a name and audit trail, so
  splitting into named agents later doesn't require a schema change.
- **Advanced ML forecasting** — exponential smoothing only (§19: "do not over-engineer
  forecasting" for MVP); the `Forecast.model_used` field makes it trivial to introduce a
  second model later and compare.
