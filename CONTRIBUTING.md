# Contributing

## Project structure

```
bizmind-bd/
├── backend/            FastAPI app (see ARCHITECTURE.md)
├── frontend/           Next.js app
├── database/seed/      Demo data generator
├── docs/               Architecture, API, database, AI, setup, deployment docs
└── tests/e2e/          Playwright browser test of the full MVP journey
```

## Backend

```bash
cd backend
pip install -r requirements.txt
pytest                      # unit/integration tests against a real Postgres test DB
alembic revision --autogenerate -m "describe change"   # after editing app/models/*
alembic upgrade head
```

Conventions:
- One router per domain in `app/api/v1/`; business logic goes in `app/services/`, never in routers.
- Every mutating endpoint that matters writes an `audit.record(...)` call (section 35).
- Every stock movement goes through `app/services/inventory.py::apply_stock_change` — never
  mutate `Product.current_stock` directly.
- New AI capabilities are added as a function in `app/services/ai/tools.py` plus an entry in
  `TOOL_SPECS`, never by giving the AI broader data access.
- RBAC is enforced with `Depends(require_role(...))` in the router — never only hidden in the frontend.

## Frontend

```bash
cd frontend
npm install
npm run dev
npm run build     # type-checks and compiles for production
```

Conventions:
- Every page renders through `useFetch` + the `<Async>` component, which handles loading,
  error+retry, and empty states uniformly (section 29) — don't hand-roll these per page.
- Reusable UI (`Button`, `Table`, `Modal`, `Badge`, toasts, page header, etc.) lives in
  `components/ui/index.tsx`. Prefer extending it over one-off styling.
- API calls go through `lib/api.ts::api()`, which attaches the JWT and turns backend errors
  into plain-language messages — never call `fetch` directly in a page.

## Running the full test suite

```bash
# Backend
cd backend && pytest

# End-to-end (needs the API on :8000, the built frontend on :3000, and demo data seeded)
python database/seed/seed.py --reset
python -m playwright install chromium   # first time only
python tests/e2e/test_mvp_journey.py
```

## Commit hygiene

Small, targeted changes. Update the relevant doc in `docs/` in the same change if you alter
architecture, the database schema, the API surface, or the AI tool layer.
