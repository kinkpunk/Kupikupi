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
| `ERROR_REPORTING_ENABLED` | yes | no | no | `1` when endpoint is configured |
| `ERROR_REPORTING_ENDPOINT_URL` | yes | no | no | absolute HTTPS error event collector URL |

Readiness must return `200` before dependent services are considered healthy:

```bash
curl https://api.staging.kupikupi.example/v1/ready
```

For `ENVIRONMENT=staging`, readiness fails if `JWT_SECRET_KEY`, `TELEGRAM_BOT_TOKEN`,
`DATABASE_URL`, `REDIS_URL`, or `CORS_ALLOWED_ORIGINS` use local/default values.
If `ERROR_REPORTING_ENABLED=1`, readiness also requires an absolute `ERROR_REPORTING_ENDPOINT_URL`.
Before deployment, use `backend/scripts/staging_preflight.py` to validate backend, bot, and WebApp
environment files together.
Use `backend/scripts/staging_env_template.py` to generate starter env files for that preflight.

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
| `BOT_POLLING_TIMEOUT_SECONDS` | yes | `30` |

If `BACKEND_ACCESS_TOKEN` is empty, the bot authenticates each Telegram sender through
`/auth/telegram-bot-user` using `TELEGRAM_BOT_TOKEN`. This is the preferred staging mode.
`TELEGRAM_WEBAPP_URL` must be an absolute HTTPS URL for field testing.
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

Backend responses include `X-Request-ID`. Send this header from clients when available, and use the
same value to correlate JSON access logs with user reports.
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
  --privacy-url https://app.staging.kupikupi.example/privacy
```

With a staging user access token, also run the authenticated flow:

```bash
cd backend
python scripts/staging_smoke.py \
  --api-base-url https://api.staging.kupikupi.example/v1 \
  --webapp-url https://app.staging.kupikupi.example \
  --access-token "$KUPIKUPI_ACCESS_TOKEN" \
  --confirm-watchlist
```

The authenticated smoke creates a shopping request and, with `--confirm-watchlist`, confirms a
watchlist. Use a staging-only test user token.

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
8. Trigger notification generation and dispatch in staging.
9. Confirm a notification is delivered to the same Telegram user.

## First Store Feed Configuration

For the first real store feed, prefer `http_csv` or `http_json` source configs before scrapers.
Use the backend operator command to print a template and apply the final config:

```bash
cd backend
python scripts/store_feed.py --print-template
python scripts/store_feed.py --config /tmp/kupikupi-store-feed.json
```

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

## Secrets Checklist

- `JWT_SECRET_KEY` generated with high entropy.
- `TELEGRAM_BOT_TOKEN` stored as a secret, not committed.
- PostgreSQL and Redis credentials stored as secrets.
- No demo access token in WebApp build args.
- Support contact and privacy policy URLs configured for WebApp and Telegram Bot.
- `TELEGRAM_ALLOWED_USER_IDS` configured for backend and Telegram Bot closed field testing.
- No localhost URLs in staging runtime config.

## Known Staging Limitations

- Store data is still demo/static unless a real `http_csv` or `http_json` source config is added.
- FX-rate freshness depends on the configured HTTP source availability.
- Error reporting dashboard setup and tracing are not yet complete.
