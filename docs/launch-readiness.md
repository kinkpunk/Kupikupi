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
- Telegram Bot command menu registration on startup.
- Telegram Bot runtime validation for WebApp URL.
- Telegram Bot closed-test allowlist by Telegram user ID.
- Telegram Bot `/id` helper for collecting tester Telegram IDs.
- Backend Telegram auth allowlist for closed field testing.
- Backend readiness validates Telegram Bot token in staging/production.
- Operator helper for building Telegram closed-test allowlist env values.
- Telegram Bot per-user backend authentication via bot-token protected exchange.
- Telegram notification delivery integration.
- Next.js Telegram WebApp MVP flow.
- WebApp authentication prefers fresh Telegram `initData` over stored or demo tokens.
- Docker Compose for local backend, worker, scheduler, WebApp, optional Telegram Bot profile.
- Staging deployment guide with environment matrix and smoke checklist.
- Live FX-rate updater job for configured currencies.
- Generic `http_csv` source adapter for affiliate or store CSV feeds.
- Operator command for creating or updating `http_csv`/`http_json` store feed configs.
- Request ID propagation and JSON access logs for backend API requests.
- In-process backend request metrics endpoint.
- Sentry-compatible HTTP error reporting hook for unhandled backend exceptions.
- PostgreSQL backup and restore procedure for staging.
- Privacy and data retention draft for closed testing.
- Scheduled retention cleanup for expired sessions, notifications, and source sync logs.
- Operator commands for user data export and account deletion by Telegram ID.
- Visible support and privacy entry points in Telegram Bot and WebApp.
- Docker Compose smoke runner for backend, worker, scheduler, WebApp, and MVP scenario.
- Remote staging smoke script for HTTPS API/WebApp and optional authenticated shopping flow.
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
- No full observability stack yet: tracing, alerting, or error reporting dashboards.
- Privacy and terms still require legal review and final hosted URLs before public beta.

## Recommended Next Iterations

1. Configure one real Czech store feed through `scripts/store_feed.py`.
2. Validate data export/deletion commands on staging restore data.
3. Add tracing, alerting, and container health dashboard notes.
4. Run the Docker Compose smoke runner and remote staging smoke on deployed staging.

## Go/No-Go Summary

- Local developer demo: go.
- Internal technical demo with demo data: go.
- Closed user test with real Telegram users: no-go until staging HTTPS and real Telegram Bot launch
  settings are in place.
- Public beta: no-go until real store data, legal review, observability, and staging validation of
  data export/deletion procedures are in place.
