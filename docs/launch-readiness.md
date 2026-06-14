# Kupikupi Launch Readiness

Status date: 2026-06-13

## Current Readiness

Kupikupi is ready for local MVP smoke testing with demo data.

Implemented and covered:

- FastAPI backend with auth, users, catalog, shopping requests, recommendations, watchlists,
  offers, price history, price analytics, deals, notifications, source sync, FX normalization,
  health and readiness checks.
- PostgreSQL migrations through `0014_fx_rates`.
- Deterministic phase 1 shopping request parser.
- Deterministic recommendation scoring by category, brand, use case, size availability, and budget.
- Deterministic source product reuse by SKU or normalized brand/category/model identity.
- Watchlist creation only after explicit user confirmation.
- Telegram Bot command flow and backend client.
- Telegram Bot polling/webhook runtime mode configuration.
- Telegram Bot command menu registration on startup.
- Telegram Bot runtime validation for WebApp URL.
- Telegram Bot closed-test allowlist by Telegram user ID.
- Telegram Bot `/id` helper for collecting tester Telegram IDs.
- Backend Telegram auth allowlist for closed field testing.
- Backend readiness validates Telegram Bot token in staging/production.
- Backend readiness validates error reporting endpoint when reporting is enabled.
- Staging environment preflight script for backend, bot, WebApp, and operator smoke config.
- Staging environment template generator for backend, bot, WebApp, and operator env files.
- Operator helper for building Telegram closed-test allowlist env values.
- Telegram Bot per-user backend authentication via bot-token protected exchange.
- Telegram notification delivery integration.
- Operator script for generating and dispatching test notifications through staging API.
- Next.js Telegram WebApp MVP flow.
- WebApp authentication prefers fresh Telegram `initData` over stored or demo tokens.
- Docker Compose for local backend, worker, scheduler, WebApp, optional Telegram Bot profile.
- Staging deployment guide with environment matrix and smoke checklist.
- Closed field test runbook with go/no-go checklist.
- Live FX-rate updater job for configured currencies.
- Generic `http_csv` source adapter for affiliate or store CSV feeds.
- Heureka-compatible store XML feed adapter with category, variant, size, color, availability, and
  CZK price extraction.
- Operator command for creating or updating `heureka_xml`/`http_csv`/`http_json` store feed configs.
- Store feed dry-run validation before database writes and field-test checklist validation for feed
  config or explicit demo-data-only mode.
- Operator source sync script with JSON summary and non-zero failure exit codes.
- Operator endpoint for reviewing potential product duplicate candidates.
- Operator endpoint for merging confirmed duplicate products.
- Operator script for listing, CSV-exporting, and merging product duplicate candidates through
  staging API.
- WebApp operator screen for reviewing duplicate candidate groups and merging confirmed duplicates.
- WebApp operator screen for creating/reviewing stores/source configs, triggering manual syncs, and
  inspecting sync-run items.
- Request ID propagation and JSON access logs for backend API requests.
- W3C `traceparent` propagation for API responses, logs, and error reports.
- In-process backend request metrics endpoint.
- Sentry-compatible HTTP error reporting hook for unhandled backend exceptions.
- Observability baseline checklist for staging dashboards and alerts.
- PostgreSQL backup and restore procedure for staging.
- Privacy and data retention draft for closed testing.
- Scheduled retention cleanup for expired sessions, notifications, and source sync logs.
- Operator commands for user data export and account deletion by Telegram ID.
- Operator smoke for validating user export/deletion on staging restore data.
- Visible support, privacy, and terms entry points in Telegram Bot and WebApp.
- Docker Compose smoke runner for backend, worker, scheduler, WebApp, and MVP scenario.
- Remote staging smoke script for HTTPS API/WebApp and optional authenticated shopping flow.
- Remote staging smoke checks for support, privacy, terms, optional admin endpoints, and opt-in
  notification admin flow.
- Closed field-test checklist script for local env/preflight/smoke-token/observability readiness.
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

## Latest Local Verification

Verified on 2026-06-13:

- Backend lint passed and all 142 tests passed.
- OpenAPI contract checks passed as part of the backend test suite.
- Alembic generated the complete PostgreSQL migration SQL through `0014_fx_rates`.
- Telegram Bot lint passed and all 37 tests passed.
- WebApp all 32 tests, TypeScript check, production build, and npm audit passed.
- Generated staging env files passed `scripts/field_test_checklist.py` in explicit demo-data mode.
- Docker smoke was not run because Docker CLI is not installed on the verification machine.

## Not Ready For Public User Testing Yet

Blocking gaps:

- No real production or staging environment is configured.
- No HTTPS public domain for WebApp/API.
- No real Telegram Bot token or deployed public bot runtime.
- Store integrations are still generic feed adapters; no live Czech store feed is configured yet.
- Product matching has deterministic cross-store reuse, punctuation/diacritic-aware normalization,
  duplicate candidate review, manual duplicate merge, operator duplicate CSV export, and WebApp
  operator review UI, but still needs validation against real store feeds.
- No full observability stack yet: tracing provider and real alerting/dashboard infrastructure still
  need setup.
- Privacy and terms still require legal review and final hosted URLs before public beta.

## Recommended Next Iterations

1. Freeze feature scope for the first closed field test.
2. Run the full local backend, Telegram Bot, WebApp, OpenAPI, and migration checks.
3. Generate real staging env files and run `scripts/field_test_checklist.py`.
4. Deploy HTTPS staging with a real Telegram Bot token and tester allowlist.
5. Run remote staging smoke and the manual Telegram scenario.
6. Configure one real Czech store feed after the demo-data field test, unless real prices are part of
   that first test's stated scope.

## Go/No-Go Summary

- Local developer demo: go.
- Internal technical demo with demo data: go.
- Closed user test with real Telegram users: no-go until staging HTTPS and real Telegram Bot launch
  settings are in place.
- Public beta: no-go until real store data, legal review, observability, and staging validation of
  data export/deletion procedures are in place.
