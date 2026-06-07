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

Backend with Telegram Bot:

```bash
docker compose -f infra/docker-compose.yml up backend worker scheduler telegram-bot
```

Backend with Telegram Bot and WebApp:

```bash
docker compose -f infra/docker-compose.yml up backend worker scheduler telegram-bot webapp
```

The backend container runs Alembic migrations on startup by default. In local Docker Compose it also
seeds MVP categories and stores. Override `RUN_MIGRATIONS` or `RUN_SEED` in the backend environment
when a different startup mode is needed.

Runtime checks:

```bash
curl http://localhost:8000/v1/health
curl http://localhost:8000/v1/ready
```

`/health` is a fast liveness check. `/ready` verifies PostgreSQL and Redis before dependent
services proceed in Docker Compose.

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

Celery tasks:

```bash
cd backend
celery -A app.core.celery_app.celery_app worker --loglevel=info
celery -A app.core.celery_app.celery_app beat --loglevel=info
celery -A app.core.celery_app.celery_app call notifications.generate
celery -A app.core.celery_app.celery_app call notifications.dispatch
celery -A app.core.celery_app.celery_app call analytics.recompute_all
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

WebApp development:

```bash
cd webapp
npm ci
npm run dev
npm test
npm run build
```

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
