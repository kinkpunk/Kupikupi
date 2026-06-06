# Kupikupi

Kupikupi is a personal shopping agent for users in Czechia.

The service accepts natural-language shopping requests, finds suitable products, compares store offers, tracks price history, and notifies users through Telegram when a good deal appears.

Example request:

```text
Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро.
```

## Current Status

Backend foundation is in progress. Telegram Bot foundation is in progress. WebApp foundation is in progress.
Implemented backend modules include users/auth, catalog, shopping requests, watchlists, offers,
price analytics, deals, notifications, Telegram delivery, Celery jobs, and the initial source sync
foundation with FX normalization.

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
docker compose -f infra/docker-compose.yml up backend worker
```

Backend with Telegram Bot:

```bash
docker compose -f infra/docker-compose.yml up backend worker telegram-bot
```

Backend with Telegram Bot and WebApp:

```bash
docker compose -f infra/docker-compose.yml up backend worker telegram-bot webapp
```

Migrations and seed data:

```bash
cd backend
alembic upgrade head
python scripts/seed.py
```

Celery tasks:

```bash
cd backend
celery -A app.core.celery_app.celery_app worker --loglevel=info
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
npm install
npm run dev
npm test
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
