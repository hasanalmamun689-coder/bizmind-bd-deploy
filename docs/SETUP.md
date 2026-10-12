# Setup

## Prerequisites

- PostgreSQL 14+
- Python 3.11+
- Node.js 18+

## 1. Database

```bash
createdb sme_intelligence
```

## 2. Backend

```bash
cd backend
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@localhost:5432/sme_intelligence
JWT_SECRET=some-long-random-string
AI_PROVIDER=none            # or "anthropic"
AI_API_KEY=                 # required only if AI_PROVIDER=anthropic
CORS_ORIGINS=http://localhost:3000
```

```bash
pip install -r requirements.txt
alembic upgrade head
python ../database/seed/seed.py     # optional: realistic Bangladeshi SME demo data
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/api/health` — should return `{"status": "ok"}`.

## 3. Frontend

```bash
cd frontend
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

Visit `http://localhost:3000`.

## Demo accounts

After running the seed script:

| Email | Password | Role |
|---|---|---|
| owner@demo.bd | Demo@1234 | Owner |
| manager@demo.bd | Demo@1234 | Manager |

## Running tests

```bash
# Backend unit/integration tests (creates its own tables in TEST_DATABASE_URL,
# defaulting to sme_intelligence_test on the same Postgres server)
createdb sme_intelligence_test
cd backend && pytest

# Browser end-to-end test of the full MVP journey
python -m playwright install chromium   # first time only
python database/seed/seed.py --reset
# with the API and built frontend (npm run build && npm start) running on :8000/:3000:
python tests/e2e/test_mvp_journey.py
```

## Enabling a live AI model

By default the AI assistant and recommendation engine work with **zero external
dependencies** — a deterministic, data-only mode that calls the same tool layer a live
model would, and is fully functional (see [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)).

To use a real model instead, set in `backend/.env`:

```env
AI_PROVIDER=anthropic
AI_API_KEY=sk-ant-...
AI_MODEL=claude-sonnet-4-6        # optional, this is the default
```

No frontend or database change is needed — `Settings → System status` will show
"Live model" once configured.

## Troubleshooting

- **`connection to server ... failed`** — PostgreSQL isn't running, or `DATABASE_URL` is wrong.
- **`relation "..." does not exist`** — run `alembic upgrade head`.
- **CORS errors in the browser** — `CORS_ORIGINS` in `backend/.env` must include the exact
  origin the frontend is served from (scheme + host + port).
- **Frontend shows "Can't reach the server"** — check `NEXT_PUBLIC_API_URL` in
  `frontend/.env.local` and that the API is running.
