# Kupikupi

Kupikupi is a personal shopping agent for users in Czechia.

The service accepts natural-language shopping requests, finds suitable products, compares store offers, tracks price history, and notifies users through Telegram when a good deal appears.

Example request:

```text
Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро.
```

## Current Status

Backend, Telegram Bot, and WebApp MVP foundations are implemented.
Implemented backend modules include users/auth, catalog, shopping requests, watchlists, offers,
price analytics, deals, notifications, Telegram delivery, Celery jobs, and source sync with FX
normalization.

CI validates backend lint/tests/migrations, Telegram Bot lint/tests, and WebApp tests/build.

## MVP Decisions

- Phase 1 uses a deterministic parser for shopping requests.
- Prices are stored in original source currency and normalized to EUR.
- Shopping requests create watchlists only after explicit user confirmation.
- Telegram WebApp is the primary user interface.
- Telegram Bot provides command-based access and notifications.

## Documentation

- [Architecture](docs/architecture.md)
- [Launch readiness](docs/launch-readiness.md)
- [Staging deployment](docs/staging-deployment.md)
- [OpenAPI draft](packages/openapi/openapi.yaml)

## Backend Development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload
```

Infrastructure services:

```bash
docker compose -f infra/docker-compose.yml up postgres redis
```

Backend with worker:

```bash
docker compose -f infra/docker-compose.yml up backend worker scheduler
```

Backend with worker and WebApp:

```bash
docker compose -f infra/docker-compose.yml up backend worker scheduler webapp
```

Backend with Telegram Bot and WebApp:

```bash
docker compose --profile telegram -f infra/docker-compose.yml up backend worker scheduler telegram-bot webapp
```

The backend container runs Alembic migrations on startup by default. In local Docker Compose it also
seeds MVP categories and stores. Override `RUN_MIGRATIONS` or `RUN_SEED` in the backend environment
when a different startup mode is needed.
The Telegram Bot service is behind the `telegram` Compose profile because it requires a real
`TELEGRAM_BOT_TOKEN`.
The WebApp Docker image receives `NEXT_PUBLIC_*` values as build args because Next.js embeds public
environment values during `next build`.

Runtime checks:

```bash
curl http://localhost:8000/v1/health
curl http://localhost:8000/v1/ready
```

`/health` is a fast liveness check. `/ready` verifies runtime configuration, PostgreSQL, and Redis
before dependent services proceed in Docker Compose. For `ENVIRONMENT=production` or `staging`,
replace the default `JWT_SECRET_KEY` and use non-localhost `DATABASE_URL`, `REDIS_URL`, and
`CORS_ALLOWED_ORIGINS`; otherwise readiness fails with `503`.

Migrations and seed data:

```bash
cd backend
alembic upgrade head
python scripts/seed.py
```

The seed command creates MVP categories, Czech stores, a demo CZK FX rate, and a Footshop
`static_json` source config with sample running-shoe offers. After seeding, run source sync to import
demo products and offers:

```bash
cd backend
celery -A app.core.celery_app.celery_app call sync.run_due_source_configs
```

MVP smoke test:

```bash
cd backend
pytest tests/test_mvp_smoke.py
```

Local database MVP smoke:

```bash
cd backend
python scripts/smoke_mvp.py
```

The smoke script seeds demo data, imports demo offers, creates a demo user shopping request,
confirms a watchlist, finds personalized deals, and generates notification records.

Local WebApp demo token:

```bash
cd backend
python scripts/demo_token.py
```

The command creates an idempotent demo user and prints `NEXT_PUBLIC_DEMO_ACCESS_TOKEN` for local
WebApp development. Use `--admin` to issue a token for an admin demo user.

Celery tasks:

```bash
cd backend
celery -A app.core.celery_app.celery_app worker --loglevel=info
celery -A app.core.celery_app.celery_app beat --loglevel=info
celery -A app.core.celery_app.celery_app call notifications.generate
celery -A app.core.celery_app.celery_app call notifications.dispatch
celery -A app.core.celery_app.celery_app call analytics.recompute_all
celery -A app.core.celery_app.celery_app call fx.update_rates
celery -A app.core.celery_app.celery_app call sync.run_fake
celery -A app.core.celery_app.celery_app call sync.run_source_config --args='["SOURCE_CONFIG_ID"]'
celery -A app.core.celery_app.celery_app call sync.run_due_source_configs
```

Telegram Bot development:

```bash
cd telegram_bot
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m bot.main
```

The bot requires `TELEGRAM_BOT_TOKEN` and an absolute `BACKEND_API_URL`.
If `BACKEND_ACCESS_TOKEN` is omitted, the bot authenticates each Telegram sender through
`/auth/telegram-bot-user` and receives a user-scoped backend token.

WebApp development:

```bash
cd webapp
npm ci
npm run dev
npm test
npm run typecheck
npm run build
```

For production-like WebApp builds, set `NEXT_PUBLIC_APP_ENV=production` or `staging` and use a
non-localhost `NEXT_PUBLIC_API_BASE_URL`. Do not set `NEXT_PUBLIC_DEMO_ACCESS_TOKEN` outside local
testing.

## Planned Stack

- Backend: FastAPI, PostgreSQL, SQLAlchemy, Alembic.
- Queue/cache: Redis, Celery.
- Store integrations: official APIs, affiliate feeds, Heureka, Playwright scrapers.
- Implemented source adapters: `static_json`, `http_json`.
- Telegram Bot: aiogram.
- WebApp: Next.js, TypeScript.
- Deployment: Docker Compose first, Kubernetes-ready later.

## Implementation Order

1. Backend foundation with migrations and tests.
2. Telegram auth and user profile.
3. Catalog, stores, and seed data.
4. Shopping request parser and recommendations.
5. Watchlists.
6. Offers, price history, and analytics.
7. Deals and notifications.
8. Source sync jobs.
9. Telegram Bot.
10. WebApp.
