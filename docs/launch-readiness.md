# Kupikupi Launch Readiness

Status date: 2026-06-17

## Current Readiness

Kupikupi is ready for local MVP smoke testing with demo data and staging workflow validation.
The real-price path is blocked on partner data access, not on missing core product code.

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
- Srovname.cz REST API adapter with API-key header auth, pagination, sale-price parsing, and
  source-sync compatible product/offer mapping.
- Operator command for creating or updating `srovname_api`/`heureka_xml`/`http_csv`/`http_json`
  store feed configs.
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

## Staging Baseline

The staging baseline is in place for a closed technical test:

- Northflank services are used for the API and Telegram Bot.
- Northflank cron jobs are used for `source_sync` and notification cycle while the deployment stays
  within the Sandbox service limits.
- PostgreSQL and Redis are provisioned for staging.
- The WebApp is deployed separately on Vercel.
- The current data-source implementation supports `static_json`, `http_json`, `http_csv`,
  `heureka_xml`, and `srovname_api`.

This does not yet validate real Czech market prices. The first real-data pass still requires a
`SROVNAME_API_KEY`, a staging `srovname_api` source config, a dry run, and a successful
`source_sync`.

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

Verified on 2026-06-17:

- Backend lint passed and all 168 tests passed.
- OpenAPI contract checks passed as part of the backend test suite.
- Telegram Bot lint passed and all 37 tests passed.
- WebApp all 41 tests and TypeScript check passed.
- Alembic migration SQL generation, WebApp production build, npm audit, generated staging env
  checklist, and Docker smoke were not run in this pass.

## Not Ready For Public User Testing Yet

Blocking gaps:

- Production is not configured.
- The Srovname partner API key is not available yet.
- No real `srovname_api` source config has been applied on staging.
- The full real-price cycle has not been validated yet:
  `Srovname API -> source sync -> offers -> watchlists -> deals -> Telegram notifications`.
- Srovname may not expose size-level availability; size-sensitive matching still needs real-data
  validation.
- Store integrations are implemented, but no live Czech store feed has been validated end to end
  yet.
- Product matching has deterministic cross-store reuse, punctuation/diacritic-aware normalization,
  duplicate candidate review, manual duplicate merge, operator duplicate CSV export, and WebApp
  operator review UI, but still needs validation against real store feeds.
- No full observability stack yet: tracing provider and real alerting/dashboard infrastructure still
  need setup.
- Privacy and terms still require legal review and final hosted URLs before public beta.

## Recommended Next Iterations

1. Freeze feature scope for the first closed field test.
2. Run the full local backend, Telegram Bot, WebApp, OpenAPI, and migration checks.
3. Run `scripts/field_test_checklist.py` against the current staging env files.
4. Run remote staging smoke and the manual Telegram scenario.
5. Keep the first closed workflow test explicitly demo-data-only unless real prices are in scope.
6. After `SROVNAME_API_KEY` is available, create the staging `srovname_api` config, run dry-run, run
   `source_sync`, review duplicate candidates, and validate matching/deals/notifications. Use
   `docs/srovname-real-data-intake.md` for the first response intake checklist.

## Go/No-Go Summary

- Local developer demo: go.
- Internal technical demo with demo data: go.
- Closed workflow test with real Telegram users and demo data: go after staging smoke, allowlist,
  support/privacy/terms, observability, and export/delete checks pass.
- Closed test that promises real prices: no-go until `SROVNAME_API_KEY`, source config, dry-run, and
  source sync pass on staging.
- Public beta: no-go until real store data, legal review, observability, and staging validation of
  data export/deletion procedures are in place.
