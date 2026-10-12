# Deployment

## Checklist (§8)

- [ ] `JWT_SECRET` is a long random value, different from the dev default, and only in
      environment variables (never committed).
- [ ] `DATABASE_URL` points at a managed/production PostgreSQL instance with backups enabled.
- [ ] `CORS_ORIGINS` lists the exact production frontend origin(s) — no wildcards.
- [ ] `AI_API_KEY` (if used) is set as a secret in the hosting platform, never in `.env` in
      the repo or in the frontend bundle (the frontend never sees this key — see
      `docs/AI_ARCHITECTURE.md`).
- [ ] `alembic upgrade head` has been run against the production database.
- [ ] The demo/seed script (`database/seed/seed.py`) is **not** run against production data
      — it's for local/demo environments only.
- [ ] `ENVIRONMENT=production` is set (surfaced read-only on the Settings page).
- [ ] HTTPS is terminated in front of both the API and the frontend (e.g. by the platform's
      load balancer/CDN) — the app itself does not do TLS.
- [ ] Frontend is built with `npm run build` and served with `npm start` (or exported as a
      standalone Node server — `next.config.js` already sets `output: "standalone"`), with
      `NEXT_PUBLIC_API_URL` pointing at the production API's public URL.
- [ ] The public site is served over HTTPS. This is required for the installable mobile
      experience and its service worker (localhost is the only development exception).

## Docker Compose (reference)

`docker-compose.yml` at the repo root brings up Postgres + the API for local integration
testing or a simple single-host deployment:

```bash
docker compose up --build
```

This does not include the frontend container (Next.js is typically deployed on a platform
like Vercel/Node hosting), or run `npm run build && npm start` behind your own process
manager/reverse proxy.

For the managed Neon + Render + Vercel setup, follow [GO_LIVE.md](GO_LIVE.md).

## Zero-downtime migrations

Alembic migrations in this codebase are additive (new tables/columns/indexes) except
`0003_unique_product_sku_per_business.py`, which will fail if duplicate `(business_id, sku)`
rows already exist — check for duplicates before applying it to a database with real data:

```sql
SELECT business_id, sku, count(*) FROM products GROUP BY 1, 2 HAVING count(*) > 1;
```

## Monitoring

The unhandled-exception handler in `app/main.py` logs the full traceback server-side
(`logger.exception(...)`) while returning only a generic message to the client — point your
log aggregator at stderr/stdout of the API process to see real errors.
