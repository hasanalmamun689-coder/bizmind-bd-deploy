# BizMind BD

> Frontend UI follows the BizMind BD draft design: dark theme, top header with health score / New Sale / AI Copilot, grouped sidebar, full-page AI Copilot. Clicking the BizMind BD logo anywhere returns to the home page (`/`).

**AI-powered SME business intelligence, analytics, forecasting, risk detection, and decision-support platform.**

Data → Insight → Prediction → Recommendation → Human Approval → Action.

Built for a small Bangladeshi retail/wholesale business (seed data uses BDT and Bangladeshi
product/supplier/customer names), but the domain model is generic.

## What this is

Not a CRUD inventory app. The system connects Sales → Inventory → Customers → Suppliers →
Procurement → Expenses → Profitability → Forecasting → Risk Detection → AI Recommendations,
and every AI-generated recommendation requires a human's explicit approval before it becomes
a purchase order — and even then only as a **DRAFT**. Nothing is ever auto-ordered.

## Web and mobile app

BizMind BD is an installable Progressive Web App (PWA), so one codebase works as both a
responsive website and an app-style experience on Android, iPhone, tablets and desktop.

- **Website:** open the deployed URL in any modern browser.
- **Android:** open it in Chrome, then choose **Install app** from the browser menu.
- **iPhone/iPad:** open it in Safari, choose **Share**, then **Add to Home Screen**.

The installed app has its own icon, launches without browser controls, and safely caches only
the visual app shell. Authentication and business data remain online-only and are never stored
by the offline cache.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL, JWT auth (python-jose + passlib/bcrypt) |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts, lucide-react |
| AI | Provider-agnostic abstraction (`app/services/ai/provider.py`): a deterministic,
data-only fallback by default, or a real Anthropic Claude call when `AI_PROVIDER=anthropic`
and `AI_API_KEY` are set. The AI only ever reads data through a closed set of 14 tool
functions (`app/services/ai/tools.py`) — it has no SQL or ORM access, and cannot place
purchase orders itself. |
| Tests | pytest (55+ backend tests against a real Postgres test database) + a Playwright
browser test (`tests/e2e/test_mvp_journey.py`) that drives the full MVP journey end-to-end |

See [ARCHITECTURE.md](docs/ARCHITECTURE.md), [DATABASE.md](docs/DATABASE.md),
[API.md](docs/API.md), [AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md),
[SETUP.md](docs/SETUP.md), [DEPLOYMENT.md](docs/DEPLOYMENT.md), [CONTRIBUTING.md](CONTRIBUTING.md).

## Quick start

```bash
# 1. Database
createdb sme_intelligence
cd backend
cp .env.example .env           # edit DATABASE_URL / JWT_SECRET as needed
pip install -r requirements.txt
alembic upgrade head
python ../database/seed/seed.py   # optional demo data

# 2. API
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd ../frontend
cp .env.example .env.local
npm install
npm run dev   # http://localhost:3000
```

Demo login (after seeding): `owner@demo.bd` / `manager@demo.bd`, password `Demo@1234`.

Full setup, environment variables and troubleshooting: [docs/SETUP.md](docs/SETUP.md).

**Deploy to the internet (Neon + Render + Vercel):** [docs/GO_LIVE.md](docs/GO_LIVE.md).

## Status against the MVP acceptance journey

The full 20-step MVP journey (register → dashboard → products → suppliers → inventory →
sales → automatic low-stock alerts → expenses → analytics → forecast → risk detection →
AI chat → AI recommendation → human approval → purchase draft → audit log) is implemented,
seeded with realistic demo data, unit-tested, and verified end-to-end through a real browser
against a real PostgreSQL database (`tests/e2e/test_mvp_journey.py`).

Deliberately deferred (per the master spec's own priority order): the native Kotlin
Android app, a multi-agent orchestration layer (a single controlled AI service layer is
used, as the spec recommends for MVP), and advanced ML forecasting beyond exponential
smoothing.
