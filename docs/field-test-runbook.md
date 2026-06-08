# Kupikupi Closed Field Test Runbook

Status date: 2026-06-08

Use this checklist before inviting real Telegram users to a closed staging test.

## Go Criteria

- API and WebApp are available through HTTPS public URLs.
- PostgreSQL and Redis are provisioned outside localhost.
- Backend `/v1/ready` returns `200`.
- Telegram Bot starts with a real staging bot token.
- Telegram WebApp URL is registered in Telegram Bot settings.
- `TELEGRAM_ALLOWED_USER_IDS` is configured in backend and Telegram Bot environments.
- At least one real or semi-real `http_csv`/`http_json` store feed is configured, or the test is
  explicitly limited to demo data.
- Support contact and privacy URLs are configured.
- Remote staging smoke passes.

## Environment Checklist

Before deploying, run the staging env preflight:

```bash
cd backend
python scripts/staging_env_template.py \
  --api-base-url https://api.staging.kupikupi.example/v1 \
  --webapp-url https://app.staging.kupikupi.example \
  --output-dir /tmp/kupikupi-staging-env
python scripts/staging_preflight.py \
  --backend-env /tmp/kupikupi-staging-env/kupikupi-backend.env \
  --bot-env /tmp/kupikupi-staging-env/kupikupi-bot.env \
  --webapp-env /tmp/kupikupi-staging-env/kupikupi-webapp.env
```

Backend API, worker, and scheduler:

- `ENVIRONMENT=staging`
- `DATABASE_URL` points to non-localhost PostgreSQL.
- `REDIS_URL` points to non-localhost Redis.
- `JWT_SECRET_KEY` is not the default.
- `TELEGRAM_BOT_TOKEN` is set.
- `TELEGRAM_ALLOWED_USER_IDS` contains the tester Telegram IDs.
- `CORS_ALLOWED_ORIGINS` contains the WebApp HTTPS origin.
- `RUN_MIGRATIONS=1` only for the migration/deploy API instance.
- `RUN_SEED=0` unless intentionally running demo data setup.

WebApp build:

- `NEXT_PUBLIC_APP_ENV=staging`
- `NEXT_PUBLIC_API_BASE_URL=https://api.staging.kupikupi.example/v1`
- `NEXT_PUBLIC_DEMO_ACCESS_TOKEN` is empty.
- `NEXT_PUBLIC_SUPPORT_CONTACT_URL` is set.
- `NEXT_PUBLIC_PRIVACY_POLICY_URL` is set.

Telegram Bot:

- `BACKEND_API_URL=https://api.staging.kupikupi.example/v1`
- `BACKEND_ACCESS_TOKEN` is empty for per-user auth.
- `TELEGRAM_WEBAPP_URL=https://app.staging.kupikupi.example`
- `TELEGRAM_ALLOWED_USER_IDS` matches the backend allowlist.
- `SUPPORT_CONTACT_URL` is set.
- `PRIVACY_POLICY_URL` is set.

## Tester Allowlist

Ask each tester to send `/id` to the staging bot, then build the allowlist:

```bash
cd backend
python scripts/telegram_allowlist.py 123456 789012
```

Set the printed `TELEGRAM_ALLOWED_USER_IDS` value in both backend and Telegram Bot environments,
then restart both services.

## Store Feed Setup

Print a feed template:

```bash
cd backend
python scripts/store_feed.py --print-template
```

Apply the feed config:

```bash
cd backend
python scripts/store_feed.py --config /tmp/kupikupi-store-feed.json
```

Run sync:

```bash
cd backend
celery -A app.core.celery_app.celery_app call sync.run_due_source_configs
```

For the first field test, it is acceptable to use demo data only if testers know the test is focused
on Telegram/WebApp flow rather than real prices.

## Smoke Checks

Run remote staging smoke:

```bash
cd backend
python scripts/staging_smoke.py \
  --api-base-url https://api.staging.kupikupi.example/v1 \
  --webapp-url https://app.staging.kupikupi.example
```

Run authenticated smoke with a staging-only user token:

```bash
cd backend
python scripts/staging_smoke.py \
  --api-base-url https://api.staging.kupikupi.example/v1 \
  --webapp-url https://app.staging.kupikupi.example \
  --access-token "$KUPIKUPI_ACCESS_TOKEN" \
  --confirm-watchlist
```

## Manual Telegram Scenario

Use a real Telegram tester account included in the allowlist:

1. Send `/start`.
2. Confirm the command menu includes `/id`, `/privacy`, `/requests`, and `/watchlists`.
3. Open the WebApp button.
4. Submit:

   ```text
   Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро.
   ```

5. Confirm parsed constraints are shown.
6. Confirm watchlist creation manually.
7. Run `/requests` and `/watchlists`.
8. Trigger notification generation and dispatch.
9. Confirm Telegram notification delivery.

## Privacy Operations

Before inviting external testers:

- Confirm support contact works.
- Confirm privacy URL opens.
- Validate user export/delete commands on staging restore data:

  ```bash
  cd backend
  python scripts/user_data.py export --telegram-id 123456 --output /tmp/kupikupi-user-123456.json
  python scripts/user_data.py delete --telegram-id 123456
  ```

Use `--confirm` only for an intentional deletion test.

## No-Go Conditions

- `/v1/ready` returns `503`.
- WebApp opens without Telegram auth or uses a demo token.
- Bot cannot authenticate users through backend.
- Tester is not blocked when missing from `TELEGRAM_ALLOWED_USER_IDS`.
- Store sync fails and the test depends on real offers.
- Support/privacy links are missing.
- Export/delete operator commands have not been validated on staging restore data.
