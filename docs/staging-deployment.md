# Kupikupi Staging Deployment

Status date: 2026-06-07

This guide defines the minimum staging environment needed before a closed user test with real
Telegram users. It is deployment-provider neutral: the same values can be mapped to Docker Compose,
PaaS services, or container orchestration.

For the final go/no-go checklist, use `docs/field-test-runbook.md`.

## Domain Assumptions

Use HTTPS for all public endpoints:

- API: `https://api.staging.kupikupi.example`
- WebApp: `https://app.staging.kupikupi.example`
- Backend API prefix: `/v1`

The final public WebApp URL registered in Telegram should be:

```text
https://app.staging.kupikupi.example
```

The backend base URL consumed by clients should be:

```text
https://api.staging.kupikupi.example/v1
```

## Required Services

- PostgreSQL 16 or compatible managed PostgreSQL.
- Redis 7 or compatible managed Redis.
- Backend API container.
- Celery worker container.
- Celery beat scheduler container.
- Next.js WebApp container.
- Telegram Bot container with either polling or webhook mode.

## Backend Runtime Environment

Set these values for the backend API, worker, and scheduler unless noted otherwise:

| Variable | Backend | Worker | Scheduler | Staging value |
| --- | --- | --- | --- | --- |
| `APP_NAME` | yes | yes | yes | `Kupikupi API` |
| `APP_VERSION` | yes | yes | yes | release version or commit SHA |
| `ENVIRONMENT` | yes | yes | yes | `staging` |
| `API_V1_PREFIX` | yes | no | no | `/v1` |
| `DATABASE_URL` | yes | yes | yes | non-localhost PostgreSQL URL |
| `REDIS_URL` | yes | yes | yes | non-localhost Redis URL |
| `JWT_SECRET_KEY` | yes | yes | yes | long random secret, not the default |
| `JWT_ALGORITHM` | yes | yes | yes | `HS256` |
| `ACCESS_TOKEN_TTL_SECONDS` | yes | yes | yes | `900` |
| `REFRESH_TOKEN_TTL_SECONDS` | yes | yes | yes | `2592000` |
| `TELEGRAM_BOT_TOKEN` | yes | yes | yes | real staging bot token |
| `TELEGRAM_ALLOWED_USER_IDS` | yes | no | no | comma-separated Telegram tester IDs |
| `CORS_ALLOWED_ORIGINS` | yes | no | no | `https://app.staging.kupikupi.example` |
| `RUN_MIGRATIONS` | yes | no | no | `1` for one API instance during deploy |
| `RUN_SEED` | yes | no | no | `0` by default |
| `SOURCE_SYNC_SCHEDULE_SECONDS` | no | yes | yes | `300` |
| `NOTIFICATIONS_GENERATE_SCHEDULE_SECONDS` | no | yes | yes | `300` |
| `NOTIFICATIONS_DISPATCH_SCHEDULE_SECONDS` | no | yes | yes | `120` |
| `ANALYTICS_RECOMPUTE_SCHEDULE_SECONDS` | no | yes | yes | `3600` |
| `FX_RATE_UPDATE_SCHEDULE_SECONDS` | no | yes | yes | `43200` |
| `RETENTION_CLEANUP_SCHEDULE_SECONDS` | no | yes | yes | `86400` |
| `NOTIFICATION_RETENTION_DAYS` | no | yes | yes | `180` |
| `SOURCE_SYNC_RETENTION_DAYS` | no | yes | yes | `90` |
| `FX_RATE_SOURCE_URL` | no | yes | yes | HTTPS JSON rates URL with EUR base |
| `FX_RATE_CURRENCIES` | no | yes | yes | `CZK` |
| `ERROR_REPORTING_ENABLED` | yes | no | no | `1` |
| `ERROR_REPORTING_ENDPOINT_URL` | yes | no | no | absolute HTTPS error event collector URL |
| `OBSERVABILITY_DASHBOARD_URL` | operator | operator | operator | absolute HTTPS dashboard URL |
| `ALERT_CONTACT_URL` | operator | operator | operator | absolute HTTPS or `mailto:` incident contact |

Readiness must return `200` before dependent services are considered healthy:

```bash
curl https://api.staging.kupikupi.example/v1/ready
```

For `ENVIRONMENT=staging`, readiness fails if `JWT_SECRET_KEY`, `TELEGRAM_BOT_TOKEN`,
`DATABASE_URL`, `REDIS_URL`, or `CORS_ALLOWED_ORIGINS` use local/default values.
Readiness also requires an absolute `ERROR_REPORTING_ENDPOINT_URL` when error reporting is enabled.
Before deployment, use `backend/scripts/staging_preflight.py` to validate backend, bot, WebApp,
operator smoke, and operator observability values together.
Use `backend/scripts/staging_env_template.py` to generate starter env files for that preflight.
Use `docs/observability.md` for the minimum dashboard and alert checklist.

## WebApp Build And Runtime Environment

Next.js embeds `NEXT_PUBLIC_*` values during `next build`, so staging values must be supplied as
Docker build args or build-time environment variables:

| Variable | Build time | Runtime | Staging value |
| --- | --- | --- | --- |
| `NEXT_PUBLIC_APP_ENV` | yes | optional | `staging` |
| `NEXT_PUBLIC_API_BASE_URL` | yes | optional | `https://api.staging.kupikupi.example/v1` |
| `NEXT_PUBLIC_DEMO_ACCESS_TOKEN` | yes | optional | empty |
| `NEXT_PUBLIC_SUPPORT_CONTACT_URL` | yes | optional | support contact URL |
| `NEXT_PUBLIC_PRIVACY_POLICY_URL` | yes | optional | privacy policy URL |
| `NEXT_PUBLIC_TERMS_URL` | yes | optional | terms URL |

Do not set `NEXT_PUBLIC_DEMO_ACCESS_TOKEN` in staging.

## Telegram Bot Environment

| Variable | Required | Staging value |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | yes | real staging bot token |
| `BACKEND_API_URL` | yes | `https://api.staging.kupikupi.example/v1` |
| `BACKEND_ACCESS_TOKEN` | no | empty for per-user auth |
| `TELEGRAM_WEBAPP_URL` | yes | `https://app.staging.kupikupi.example` |
| `TELEGRAM_ALLOWED_USER_IDS` | no | same comma-separated Telegram tester IDs as backend |
| `SUPPORT_CONTACT_URL` | yes | support contact URL |
| `PRIVACY_POLICY_URL` | yes | privacy policy URL |
| `TERMS_URL` | yes | terms URL |
| `BOT_RUN_MODE` | yes | `polling` for simple staging, `webhook` behind HTTPS ingress |
| `BOT_POLLING_TIMEOUT_SECONDS` | yes | `30` |
| `TELEGRAM_WEBHOOK_URL` | webhook only | `https://bot.staging.kupikupi.example/telegram/webhook` |
| `TELEGRAM_WEBHOOK_SECRET` | webhook only | long random secret |
| `TELEGRAM_WEBHOOK_PATH` | webhook only | `/telegram/webhook` |
| `WEBHOOK_HOST` | webhook only | `0.0.0.0` |
| `WEBHOOK_PORT` | webhook only | `8080` |

If `BACKEND_ACCESS_TOKEN` is empty, the bot authenticates each Telegram sender through
`/auth/telegram-bot-user` using `TELEGRAM_BOT_TOKEN`. This is the preferred staging mode.
`TELEGRAM_WEBAPP_URL` must be an absolute HTTPS URL for field testing.

## Operator Smoke Environment

| Variable | Required | Staging value |
| --- | --- | --- |
| `KUPIKUPI_API_BASE_URL` | yes | `https://api.staging.kupikupi.example/v1` |
| `KUPIKUPI_WEBAPP_URL` | yes | `https://app.staging.kupikupi.example` |
| `KUPIKUPI_SUPPORT_URL` | yes | support contact URL |
| `KUPIKUPI_PRIVACY_URL` | yes | privacy policy URL |
| `KUPIKUPI_TERMS_URL` | yes | terms URL |
| `KUPIKUPI_ACCESS_TOKEN` | optional | staging-only user token for authenticated smoke |
| `KUPIKUPI_ADMIN_ACCESS_TOKEN` | yes | staging admin token for admin smoke and duplicate review |
| `KUPIKUPI_CONFIRM_WATCHLIST` | yes | `0` by default, `1` for watchlist confirmation smoke |
| `KUPIKUPI_RUN_NOTIFICATION_SMOKE` | yes | `0` by default, `1` when notification smoke may run |
| `KUPIKUPI_NOTIFICATION_DISPATCH_LIMIT` | yes | `100` |
For the first closed test, `BOT_RUN_MODE=polling` is acceptable and operationally simpler. Use
`BOT_RUN_MODE=webhook` when the bot container is exposed through HTTPS ingress and set
`TELEGRAM_WEBHOOK_SECRET` as a secret.
For a closed field test, set `TELEGRAM_ALLOWED_USER_IDS` in both backend and Telegram Bot
environments. The backend enforces the allowlist for Telegram WebApp and Bot auth. Leave it empty
only for open testing. Testers can send `/id` to the staging bot to see the numeric Telegram ID that
must be added to the allowlist.
Build the env value with:

```bash
cd backend
python scripts/telegram_allowlist.py 123456 789012
```

## Deployment Order

1. Provision PostgreSQL and Redis.
2. Configure DNS and HTTPS for API and WebApp.
3. Build WebApp with staging `NEXT_PUBLIC_*` values.
4. Deploy backend API with `RUN_MIGRATIONS=1` for the migration step.
5. Start worker and scheduler with `RUN_MIGRATIONS=0` and `RUN_SEED=0`.
6. Verify `/v1/health` and `/v1/ready`.
7. Deploy Telegram Bot with real staging bot token and WebApp URL.
8. Register the staging WebApp URL in Telegram Bot settings.
   The bot registers its command menu on startup.
9. Run remote staging smoke checks.
10. Run manual Telegram field-test checks.

Backend responses include `X-Request-ID` and `traceparent`. Send these headers from clients when
available, and use the same values to correlate JSON access logs, error reports, and user reports.
Basic in-process request counters are available at `/v1/metrics`.

Before deploying migrations or opening staging to testers, follow the PostgreSQL backup and restore
procedure in `docs/postgres-backup-restore.md`.
For closed user testing, use the privacy and retention draft in
`docs/privacy-data-retention.md` as the operator baseline.
The scheduler runs `retention.cleanup` daily by default to remove expired refresh token sessions,
old notification records, and old source sync logs.
Validate user export and deletion commands against a restored staging backup before enabling
external testers:

```bash
cd backend
python scripts/user_data_smoke.py \
  --telegram-id 123456 \
  --export-output /tmp/kupikupi-user-123456.json \
  --confirm-delete
```

Run this only against restored staging data or a staging-only test user.

## Staging Smoke Checks

Before a remote staging smoke, run the local Docker smoke runner on a machine with Docker:

```bash
scripts/docker-smoke.sh --down
```

Then run the remote staging smoke against HTTPS endpoints:

```bash
cd backend
python scripts/staging_smoke.py \
  --api-base-url https://api.staging.kupikupi.example/v1 \
  --webapp-url https://app.staging.kupikupi.example \
  --support-url mailto:support@example.test \
  --privacy-url https://app.staging.kupikupi.example/privacy \
  --terms-url https://app.staging.kupikupi.example/terms
```

With a staging user access token, also run the authenticated flow:

```bash
cd backend
python scripts/staging_smoke.py \
  --api-base-url https://api.staging.kupikupi.example/v1 \
  --webapp-url https://app.staging.kupikupi.example \
  --access-token "$KUPIKUPI_ACCESS_TOKEN" \
  --admin-access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" \
  --confirm-watchlist \
  --run-notification-smoke
```

The authenticated smoke creates a shopping request and, with `--confirm-watchlist`, confirms a
watchlist. The admin smoke verifies operator access to sync runs and duplicate candidate review.
Use staging-only user and admin tokens. Enable notification smoke only when staging is ready to
generate and dispatch test notifications.

Use a real Telegram account allowed to access the staging bot:

1. Open `/start` in the staging Telegram Bot.
2. Open the WebApp button.
3. Verify that WebApp authenticates through Telegram `initData`.
4. Submit:

   ```text
   Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро.
   ```

5. Confirm that parser output is shown.
6. Confirm watchlist creation manually.
7. Verify `/requests` and `/watchlists` in the Telegram Bot.
8. Trigger notification generation and dispatch in staging:

   ```bash
   python scripts/notifications.py \
     --api-base-url https://api.staging.kupikupi.example/v1 \
     --access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" \
     generate
   python scripts/notifications.py \
     --api-base-url https://api.staging.kupikupi.example/v1 \
     --access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" \
     dispatch --limit 100
   ```

9. Confirm a notification is delivered to the same Telegram user.

## First Store Feed Configuration

For the first real store feed, prefer `http_csv` or `http_json` source configs before scrapers.
Use the backend operator command to print a template and apply the final config:

```bash
cd backend
python scripts/store_feed.py --print-template
python scripts/store_feed.py --config /tmp/kupikupi-store-feed.json --dry-run --limit 3 --min-offers 1
python scripts/store_feed.py --config /tmp/kupikupi-store-feed.json
python scripts/source_sync.py --due --limit 10
```

The dry run validates the JSON config, downloads the feed through the configured adapter, and prints
`offers_seen`, quality counters, warnings, and a small sample without writing to the database. It
fails if the feed returns fewer than `--min-offers` offers. Apply the config only after the sample
has plausible product URLs, prices, currencies, category values, and sizes.
The sync command prints a JSON summary and returns a non-zero exit code if any run fails or partially
fails.

Example `http_csv` source config settings:

```json
{
  "delimiter": ",",
  "size_delimiter": "|",
  "columns": {
    "external_id": "id",
    "product_url": "url",
    "source_price": "price",
    "source_old_price": "old_price",
    "source_currency": "currency",
    "product_name": "name",
    "brand_name": "brand",
    "category_slug": "category",
    "category_name": "category_name",
    "model": "model",
    "sku": "sku",
    "image_url": "image_url",
    "sizes": "sizes"
  },
  "defaults": {
    "source_currency": "CZK",
    "availability": "in_stock",
    "size_system": "EU"
  }
}
```

Required logical fields are `external_id`, `product_url`, `source_price`, and `product_name`.
`source_currency` may come from a column or `defaults.source_currency`.
After the first sync, review potential product duplicates:

```bash
cd backend
python scripts/product_duplicates.py \
  --api-base-url https://api.staging.kupikupi.example/v1 \
  --access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" \
  list
python scripts/product_duplicates.py \
  --api-base-url https://api.staging.kupikupi.example/v1 \
  --access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" \
  list --format csv --output /tmp/kupikupi-duplicate-candidates.csv
```

The command groups products by category, brand, and normalized model/name so the operator can spot
duplicates. Use the CSV export for bulk review notes, then merge confirmed duplicates into the
canonical target product:

```bash
python scripts/product_duplicates.py \
  --api-base-url https://api.staging.kupikupi.example/v1 \
  --access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" \
  merge \
  --source-product-id SOURCE_PRODUCT_UUID \
  --target-product-id TARGET_PRODUCT_UUID
```

## Secrets Checklist

- `JWT_SECRET_KEY` generated with high entropy.
- `TELEGRAM_BOT_TOKEN` stored as a secret, not committed.
- PostgreSQL and Redis credentials stored as secrets.
- No demo access token in WebApp build args.
- Support contact, privacy policy, and terms URLs configured for WebApp and Telegram Bot.
- Error reporting endpoint, observability dashboard, and alert contact configured.
- `TELEGRAM_ALLOWED_USER_IDS` configured for backend and Telegram Bot closed field testing.
- No localhost URLs in staging runtime config.

## Known Staging Limitations

- Store data is still demo/static unless a real `http_csv` or `http_json` source config is added.
- FX-rate freshness depends on the configured HTTP source availability.
- Product duplicate candidates can be reviewed and merged, but bulk review tooling is not
  implemented yet.
- Full distributed tracing is not yet complete.
