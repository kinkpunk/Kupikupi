# Kupikupi Staging Deployment

Status date: 2026-06-07

This guide defines the minimum staging environment needed before a closed user test with real
Telegram users. It is deployment-provider neutral: the same values can be mapped to Docker Compose,
PaaS services, or container orchestration.

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
| `CORS_ALLOWED_ORIGINS` | yes | no | no | `https://app.staging.kupikupi.example` |
| `RUN_MIGRATIONS` | yes | no | no | `1` for one API instance during deploy |
| `RUN_SEED` | yes | no | no | `0` by default |
| `SOURCE_SYNC_SCHEDULE_SECONDS` | no | yes | yes | `300` |
| `NOTIFICATIONS_GENERATE_SCHEDULE_SECONDS` | no | yes | yes | `300` |
| `NOTIFICATIONS_DISPATCH_SCHEDULE_SECONDS` | no | yes | yes | `120` |
| `ANALYTICS_RECOMPUTE_SCHEDULE_SECONDS` | no | yes | yes | `3600` |
| `FX_RATE_UPDATE_SCHEDULE_SECONDS` | no | yes | yes | `43200` |
| `FX_RATE_SOURCE_URL` | no | yes | yes | HTTPS JSON rates URL with EUR base |
| `FX_RATE_CURRENCIES` | no | yes | yes | `CZK` |

Readiness must return `200` before dependent services are considered healthy:

```bash
curl https://api.staging.kupikupi.example/v1/ready
```

For `ENVIRONMENT=staging`, readiness fails if `JWT_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, or
`CORS_ALLOWED_ORIGINS` use local/default values.

## WebApp Build And Runtime Environment

Next.js embeds `NEXT_PUBLIC_*` values during `next build`, so staging values must be supplied as
Docker build args or build-time environment variables:

| Variable | Build time | Runtime | Staging value |
| --- | --- | --- | --- |
| `NEXT_PUBLIC_APP_ENV` | yes | optional | `staging` |
| `NEXT_PUBLIC_API_BASE_URL` | yes | optional | `https://api.staging.kupikupi.example/v1` |
| `NEXT_PUBLIC_DEMO_ACCESS_TOKEN` | yes | optional | empty |

Do not set `NEXT_PUBLIC_DEMO_ACCESS_TOKEN` in staging.

## Telegram Bot Environment

| Variable | Required | Staging value |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | yes | real staging bot token |
| `BACKEND_API_URL` | yes | `https://api.staging.kupikupi.example/v1` |
| `BACKEND_ACCESS_TOKEN` | no | empty for per-user auth |
| `TELEGRAM_WEBAPP_URL` | yes | `https://app.staging.kupikupi.example` |
| `BOT_POLLING_TIMEOUT_SECONDS` | yes | `30` |

If `BACKEND_ACCESS_TOKEN` is empty, the bot authenticates each Telegram sender through
`/auth/telegram-bot-user` using `TELEGRAM_BOT_TOKEN`. This is the preferred staging mode.

## Deployment Order

1. Provision PostgreSQL and Redis.
2. Configure DNS and HTTPS for API and WebApp.
3. Build WebApp with staging `NEXT_PUBLIC_*` values.
4. Deploy backend API with `RUN_MIGRATIONS=1` for the migration step.
5. Start worker and scheduler with `RUN_MIGRATIONS=0` and `RUN_SEED=0`.
6. Verify `/v1/health` and `/v1/ready`.
7. Deploy Telegram Bot with real staging bot token and WebApp URL.
8. Register the staging WebApp URL in Telegram Bot settings.
9. Run staging smoke checks.

Backend responses include `X-Request-ID`. Send this header from clients when available, and use the
same value to correlate JSON access logs with user reports.

Before deploying migrations or opening staging to testers, follow the PostgreSQL backup and restore
procedure in `docs/postgres-backup-restore.md`.

## Staging Smoke Checks

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
- No localhost URLs in staging runtime config.

## Known Staging Limitations

- Store data is still demo/static unless a real `http_csv` or `http_json` source config is added.
- FX-rate freshness depends on the configured HTTP source availability.
- Metrics and error reporting dashboards are not yet complete.
