# Kupikupi Launch Readiness

Status date: 2026-06-07

## Current Readiness

Kupikupi is ready for local MVP smoke testing with demo data.

Implemented and covered:

- FastAPI backend with auth, users, catalog, shopping requests, recommendations, watchlists,
  offers, price history, price analytics, deals, notifications, source sync, FX normalization,
  health and readiness checks.
- PostgreSQL migrations through `0014_fx_rates`.
- Deterministic phase 1 shopping request parser.
- Watchlist creation only after explicit user confirmation.
- Telegram Bot command flow and backend client.
- Telegram Bot per-user backend authentication via bot-token protected exchange.
- Telegram notification delivery integration.
- Next.js Telegram WebApp MVP flow.
- WebApp authentication prefers fresh Telegram `initData` over stored or demo tokens.
- Docker Compose for local backend, worker, scheduler, WebApp, optional Telegram Bot profile.
- Staging deployment guide with environment matrix and smoke checklist.
- Live FX-rate updater job for configured currencies.
- Generic `http_csv` source adapter for affiliate or store CSV feeds.
- CI for backend, Telegram Bot, WebApp, OpenAPI contract checks, migrations, audit, typecheck,
  builds, and Docker image builds.
- Demo seed, demo token helper, and local MVP smoke script.

## Local MVP Test Scope

The current local MVP can demonstrate:

1. Seed MVP categories, Czech stores, demo FX rate, and static Footshop source config.
2. Import demo running-shoe offers.
3. Create a demo user token.
4. Submit a natural-language shopping request.
5. Show deterministic parser output.
6. Show recommendations and current offers.
7. Confirm watchlist creation after user action.
8. Generate personalized deals and notification records.
9. Open WebApp locally with demo token.

## Not Ready For Public User Testing Yet

Blocking gaps:

- No real production or staging environment is configured.
- No HTTPS public domain for WebApp/API.
- No real Telegram Bot token and webhook/polling deployment configuration for a public bot.
- Store integrations are still generic feed adapters; no live Czech store feed is configured yet.
- Product matching is basic deterministic matching by category/product data, not robust
  cross-store normalization.
- No observability stack yet: structured request logs, metrics, tracing, alerting, or error
  reporting dashboards.
- No backup/restore procedure for PostgreSQL.
- No privacy policy, terms, or user-facing data retention controls.

## Recommended Next Iterations

1. Configure one real Czech store feed through `http_csv` or `http_json`.
2. Add basic observability: JSON logs, request IDs, Sentry-compatible error hooks, and container
   health dashboard notes.
3. Add backup/restore instructions for PostgreSQL.
4. Run end-to-end Docker Compose smoke on a machine with Docker available.

## Go/No-Go Summary

- Local developer demo: go.
- Internal technical demo with demo data: go.
- Closed user test with real Telegram users: no-go until staging HTTPS and real Telegram Bot launch
  settings are in place.
- Public beta: no-go until real store data, privacy/legal basics, observability, and backup/restore
  are in place.
