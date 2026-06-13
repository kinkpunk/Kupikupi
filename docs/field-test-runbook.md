# Kupikupi Closed Field Test Runbook

Status date: 2026-06-13

Use this checklist before inviting real Telegram users to a closed staging test.

The first field test is a workflow validation, not a public beta. Do not delay it for additional
admin UI, parser improvements, store adapters, or distributed tracing when the go criteria below
are already satisfied.

## Go Criteria

- API and WebApp are available through HTTPS public URLs.
- PostgreSQL and Redis are provisioned outside localhost.
- Backend `/v1/ready` returns `200`.
- Telegram Bot starts with a real staging bot token.
- Telegram WebApp URL is registered in Telegram Bot settings.
- `TELEGRAM_ALLOWED_USER_IDS` is configured in backend and Telegram Bot environments.
- At least one real or semi-real `http_csv`/`http_json` store feed is configured, or the test is
  explicitly limited to demo data.
- Support contact, privacy, and terms URLs are configured.
- Error reporting, observability dashboard, and alert contact are configured.
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
  --webapp-env /tmp/kupikupi-staging-env/kupikupi-webapp.env \
  --operator-env /tmp/kupikupi-staging-env/kupikupi-operator.env
python scripts/field_test_checklist.py --env-dir /tmp/kupikupi-staging-env
```

The checklist is local-only: it validates env files, runs preflight, validates the store feed config
or explicit demo-data mode, flags missing smoke tokens, checks observability links, and prints the
next operator commands.

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
- `NEXT_PUBLIC_TERMS_URL` is set.

Telegram Bot:

- `BACKEND_API_URL=https://api.staging.kupikupi.example/v1`
- `BACKEND_ACCESS_TOKEN` is empty for per-user auth.
- `TELEGRAM_WEBAPP_URL=https://app.staging.kupikupi.example`
- `TELEGRAM_ALLOWED_USER_IDS` matches the backend allowlist.
- `BOT_RUN_MODE=polling` for simple staging, or `webhook` with HTTPS ingress.
- If `BOT_RUN_MODE=webhook`, `TELEGRAM_WEBHOOK_URL`, `TELEGRAM_WEBHOOK_SECRET`, and
  `TELEGRAM_WEBHOOK_PATH` are configured.
- `SUPPORT_CONTACT_URL` is set.
- `PRIVACY_POLICY_URL` is set.
- `TERMS_URL` is set.

Operator smoke environment:

- `KUPIKUPI_API_BASE_URL=https://api.staging.kupikupi.example/v1`
- `KUPIKUPI_WEBAPP_URL=https://app.staging.kupikupi.example`
- `KUPIKUPI_SUPPORT_URL` is set.
- `KUPIKUPI_PRIVACY_URL` is set.
- `KUPIKUPI_TERMS_URL` is set.
- `KUPIKUPI_ADMIN_ACCESS_TOKEN` is set for admin smoke and duplicate review.
- `KUPIKUPI_CONFIRM_WATCHLIST` is `0` or `1`.
- `KUPIKUPI_RUN_NOTIFICATION_SMOKE` is `0` or `1`.
- `KUPIKUPI_NOTIFICATION_DISPATCH_LIMIT` is a positive integer.
- `KUPIKUPI_STORE_FEED_CONFIG` points to the local JSON feed config for dry-run/apply.
- `KUPIKUPI_DEMO_DATA_ONLY` is `0`, unless the test is explicitly limited to demo data.

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
python scripts/store_feed.py --config "$KUPIKUPI_STORE_FEED_CONFIG" --dry-run --limit 3 --min-offers 1
python scripts/store_feed.py --config "$KUPIKUPI_STORE_FEED_CONFIG"
```

The dry run must pass and show at least one offer, product details, EUR prices, size coverage for
size-sensitive categories, and a plausible sample before applying the config.
If `KUPIKUPI_DEMO_DATA_ONLY=1`, skip this section and tell testers the run does not validate real
prices.

Run sync:

```bash
cd backend
python scripts/source_sync.py --due --limit 10
```

The sync report must show `failed=0` and `partially_failed=0`. For a single known config, use
`python scripts/source_sync.py --source-config-id SOURCE_CONFIG_UUID`.

Review potential duplicate products after the sync:

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

Merge only obvious duplicates into the canonical product:

```bash
python scripts/product_duplicates.py \
  --api-base-url https://api.staging.kupikupi.example/v1 \
  --access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" \
  merge \
  --source-product-id SOURCE_PRODUCT_UUID \
  --target-product-id TARGET_PRODUCT_UUID
```

For the first field test, it is acceptable to use demo data only if testers know the test is focused
on Telegram/WebApp flow rather than real prices.

## Smoke Checks

Run remote staging smoke:

```bash
cd backend
python scripts/staging_smoke.py \
  --api-base-url https://api.staging.kupikupi.example/v1 \
  --webapp-url https://app.staging.kupikupi.example \
  --support-url mailto:support@example.test \
  --privacy-url https://app.staging.kupikupi.example/privacy \
  --terms-url https://app.staging.kupikupi.example/terms
```

Run authenticated smoke with a staging-only user token:

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

The smoke report must show `admin-sync-runs=ok` and `admin-duplicate-candidates=ok` when an admin
token is supplied. Enable notification smoke only when test notifications may be generated and
dispatched.

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
8. Trigger notification generation and dispatch:

   ```bash
   cd backend
   python scripts/notifications.py \
     --api-base-url https://api.staging.kupikupi.example/v1 \
     --access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" \
     generate
   python scripts/notifications.py \
     --api-base-url https://api.staging.kupikupi.example/v1 \
     --access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" \
     dispatch --limit 100
   ```

9. Confirm Telegram notification delivery.

## Privacy Operations

Before inviting external testers:

- Confirm support contact works.
- Confirm privacy URL opens.
- Confirm terms URL opens.
- Open the observability dashboard and confirm `/v1/ready`, request volume, error rate, and
  notification dispatch panels are visible.
- Validate user export/delete commands on staging restore data:

  ```bash
  cd backend
  python scripts/user_data_smoke.py \
    --telegram-id 123456 \
    --export-output /tmp/kupikupi-user-123456.json \
    --confirm-delete
  ```

Use only a restored staging backup or a staging-only test user because this smoke performs an
intentional deletion after the export and dry run.

## No-Go Conditions

- `/v1/ready` returns `503`.
- WebApp opens without Telegram auth or uses a demo token.
- Bot cannot authenticate users through backend.
- Tester is not blocked when missing from `TELEGRAM_ALLOWED_USER_IDS`.
- Store sync fails and the test depends on real offers.
- Support/privacy/terms links are missing.
- Observability dashboard or alert contact is missing.
- Export/delete operator commands have not been validated on staging restore data.
