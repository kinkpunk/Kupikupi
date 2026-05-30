# Kupikupi

Kupikupi is a personal shopping agent for users in Czechia.

The service accepts natural-language shopping requests, finds suitable products, compares store offers, tracks price history, and notifies users through Telegram when a good deal appears.

Example request:

```text
Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро.
```

## Current Status

Architecture baseline only. Backend, Telegram Bot, and WebApp implementation have not started yet.

## MVP Decisions

- Phase 1 uses a deterministic parser for shopping requests.
- Prices are stored in original source currency and normalized to EUR.
- Shopping requests create watchlists only after explicit user confirmation.
- Telegram WebApp is the primary user interface.
- Telegram Bot provides command-based access and notifications.

## Documentation

- [Architecture](docs/architecture.md)
- [OpenAPI draft](packages/openapi/openapi.yaml)

## Planned Stack

- Backend: FastAPI, PostgreSQL, SQLAlchemy, Alembic.
- Queue/cache: Redis, Celery.
- Store integrations: official APIs, affiliate feeds, Heureka, Playwright scrapers.
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
7. Source sync jobs.
8. Deals and notifications.
9. Telegram Bot.
10. WebApp.
