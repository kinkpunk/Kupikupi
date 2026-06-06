# Kupikupi: Architecture Draft

Status: approval draft  
Scope: architecture, project structure, database model, API contract  
Implementation: not started

## Product Positioning

Kupikupi should be treated as a personal shopping agent, not only as a product monitor.

The user may write a natural-language request:

> Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро.

The service should:

- understand intent, category, constraints, size, budget, country, and delivery needs;
- find suitable products and offers in supported Czech stores;
- normalize product names across stores;
- compare current prices, historical prices, discounts, availability, sizes, and delivery;
- create shortlists or watchlists;
- notify the user when a materially good offer appears.

Watchlists remain part of the domain, but they are an internal/user-facing mechanism of the shopping agent.

## MVP Boundaries

Included:

- Telegram registration and authentication;
- Telegram Bot command flow;
- Telegram WebApp as the main UI;
- natural-language shopping requests;
- deterministic parser for phase 1 shopping request extraction;
- watchlist creation only after explicit user confirmation;
- watchlist management;
- product matching and normalization;
- Czech store integrations;
- price collection in source currency plus normalized EUR values;
- price history;
- price analytics;
- Telegram notifications;
- admin store/source controls;
- Docker Compose deployment;
- tests and migrations for every implementation iteration.

Excluded from MVP:

- automatic purchase;
- in-app payments;
- mobile apps;
- multi-country support;
- AI-based parsing and normalization;
- non-Czech marketplaces.

## High-Level Architecture

```mermaid
flowchart LR
    U["User"] --> TG["Telegram Bot"]
    U --> WA["Telegram WebApp"]

    TG --> API["FastAPI Backend"]
    WA --> API

    API --> AUTH["Auth Module"]
    API --> AGENT["Shopping Agent"]
    API --> WL["Watchlist Module"]
    API --> DEALS["Deals Module"]
    API --> ADMIN["Admin Module"]

    AGENT --> INTENT["Deterministic Intent Parser"]
    AGENT --> MATCH["Product Matching Engine"]
    AGENT --> RANK["Offer Ranking"]

    API --> DB[("PostgreSQL")]
    API --> CACHE[("Redis")]

    API --> QUEUE["Celery Queue"]
    QUEUE --> COLLECT["Price Collection Workers"]
    QUEUE --> NOTIFY["Notification Workers"]
    QUEUE --> ANALYTICS["Analytics Workers"]

    COLLECT --> FEEDS["APIs / XML / CSV / Heureka"]
    COLLECT --> SCRAPERS["Playwright Scrapers"]
    NOTIFY --> TGAPI["Telegram API"]

    COLLECT --> DB
    ANALYTICS --> DB
    NOTIFY --> DB
```

## Backend Modules

- `auth`: Telegram login validation, JWT issue/refresh, current user context.
- `users`: profile, settings, notification preferences.
- `shopping_requests`: natural-language request intake, deterministic parsed constraints, generated recommendations.
- `catalog`: products, brands, categories, variants, sizes, colors.
- `stores`: store metadata, source configuration, delivery support, source health.
- `offers`: current store offers, availability, size/color availability, product URLs.
- `prices`: immutable price history, source currency values, normalized EUR values, analytics snapshots.
- `matching`: product normalization, duplicate detection, store-specific mappings.
- `watchlists`: exact product, category, brand, and confirmed agent-created watchlists.
- `deals`: current best deals and ranked recommendations.
- `notifications`: notification events, deduplication, Telegram delivery.
- `admin`: store/source management, manual sync runs, logs.
- `jobs`: Celery tasks for sync, analytics, notification dispatch.

## Data Collection Priority

1. Official APIs.
2. Affiliate XML/CSV feeds.
3. Heureka integration.
4. Playwright scrapers.

Every source adapter should expose the same internal contract:

- fetch catalog/products;
- fetch current offers;
- fetch variants/sizes/colors;
- fetch delivery availability when supported;
- report health and parser errors.

## Suggested Tech Stack

- Backend: FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic.
- Database: PostgreSQL.
- Cache and locks: Redis.
- Queue: Celery + Redis broker.
- Scraping: Playwright.
- Telegram Bot: aiogram.
- WebApp: Next.js, TypeScript.
- Tests: pytest, pytest-asyncio, httpx, testcontainers or dockerized PostgreSQL.
- CI: lint, typecheck, tests, migration check, Docker build.

## Repository Structure

```text
kupikupi/
  backend/
    app/
      main.py
      api/
        deps.py
        router.py
        v1/
          auth.py
          users.py
          shopping_requests.py
          watchlists.py
          products.py
          offers.py
          deals.py
          price_history.py
          notifications.py
          admin.py
      core/
        config.py
        security.py
        logging.py
        celery_app.py
      db/
        session.py
        base.py
        migrations/
      domains/
        auth/
        users/
        shopping_requests/
        catalog/
        stores/
        offers/
        prices/
        matching/
        watchlists/
        deals/
        notifications/
        admin/
      integrations/
        telegram/
        stores/
          base.py
          footshop.py
          queens.py
          zalando.py
          about_you.py
          sportisimo.py
          notino.py
          dr_max.py
          pilulka.py
          rohlik.py
          kosik.py
        heureka/
      jobs/
        sync_prices.py
        compute_analytics.py
        send_notifications.py
      tests/
        unit/
        integration/
        contract/
    alembic.ini
    pyproject.toml
    Dockerfile

  bot/
    app/
      main.py
      handlers/
        start.py
        watch.py
        list.py
        delete.py
        pause.py
        settings.py
        help.py
      keyboards/
      api_client/
      config.py
    tests/
    pyproject.toml
    Dockerfile

  webapp/
    src/
      app/
      components/
      features/
        dashboard/
        shopping-request/
        watchlists/
        products/
        deals/
        settings/
      lib/
        api.ts
        telegram.ts
      styles/
    tests/
    package.json
    Dockerfile

  packages/
    openapi/
      openapi.yaml
    shared-types/

  infra/
    docker-compose.yml
    docker-compose.test.yml
    nginx/
    scripts/

  docs/
    architecture.md
    deployment.md
    api.md
    development.md

  .github/
    workflows/
      ci.yml
```

## Iterative Implementation Plan

1. Backend foundation:
   FastAPI app, config, PostgreSQL, Alembic, healthcheck, auth skeleton, CI, first tests.

2. Users and Telegram auth:
   Telegram init data validation, JWT, user profile, settings, migrations, API tests.

3. Catalog and stores:
   categories, brands, products, stores, variants, seed data, admin APIs, tests.

4. Shopping requests:
   natural-language request intake, parsed constraints schema, deterministic parser, recommendation draft model, tests.

5. Watchlists:
   exact/category/brand rules, CRUD, archive/pause/delete, creation from shopping request after user confirmation, migrations, tests.

6. Offers and price history:
   offer model, source currency and EUR-normalized prices, price snapshots, analytics tables, price-history API, tests.

7. Source adapters and sync jobs:
   first feed/scraper adapter, Celery sync, source logs, tests with fixtures.

8. Deals and ranking:
   current best offers, historical-low logic, lowest-10-percent logic, tests.

9. Notifications:
   notification rules, deduplication, Telegram dispatch, tests.

10. Telegram Bot:
    `/start`, `/watch`, `/list`, `/delete`, `/pause`, `/settings`, `/help`, backend integration tests.

11. WebApp:
    dashboard, shopping request form, watchlists, product page, deals feed, settings, UI tests.

## ER Diagram

```mermaid
erDiagram
    users ||--o{ shopping_requests : creates
    users ||--o{ watchlists : owns
    users ||--o{ notifications : receives
    users ||--o{ user_sessions : has

    shopping_requests ||--o{ shopping_request_constraints : parsed_into
    shopping_requests ||--o{ recommendations : produces
    recommendations }o--|| products : references
    recommendations }o--o| offers : best_offer

    categories ||--o{ products : contains
    brands ||--o{ products : owns
    products ||--o{ product_variants : has
    products ||--o{ product_aliases : normalized_by
    products ||--o{ offers : listed_as
    products ||--o{ price_analytics : summarized_by

    stores ||--o{ source_configs : uses
    stores ||--o{ offers : publishes
    stores ||--o{ source_sync_runs : logs
    stores ||--o{ source_product_mappings : maps

    source_configs ||--o{ source_product_mappings : identifies
    source_configs ||--o{ source_sync_runs : runs
    source_product_mappings }o--|| products : links
    offers ||--o{ price_snapshots : records
    offers ||--o{ offer_availability : has
    product_variants ||--o{ offer_availability : maps_to

    watchlists }o--o| products : exact_product
    watchlists }o--o| categories : category_rule
    watchlists }o--o| brands : brand_rule
    watchlists ||--o{ watchlist_matches : matches
    watchlist_matches }o--|| offers : matched_offer

    watchlists ||--o{ notifications : triggers
    notifications }o--o| offers : about
    notifications }o--o| shopping_requests : about_request

    users {
        uuid id PK
        bigint telegram_id UK
        text username
        text first_name
        text last_name
        text language
        text country
        text currency
        boolean is_admin
        timestamptz created_at
        timestamptz updated_at
    }

    user_sessions {
        uuid id PK
        uuid user_id FK
        text refresh_token_hash
        timestamptz expires_at
        timestamptz created_at
    }

    shopping_requests {
        uuid id PK
        uuid user_id FK
        text raw_text
        text status
        text locale
        text display_currency
        numeric budget_amount
        timestamptz created_at
        timestamptz updated_at
    }

    shopping_request_constraints {
        uuid id PK
        uuid request_id FK
        text category
        text use_case
        text size_value
        text size_system
        text preferred_brand
        text color
        numeric max_price
        text max_price_currency
        jsonb attributes
    }

    recommendations {
        uuid id PK
        uuid request_id FK
        uuid product_id FK
        uuid best_offer_id FK
        numeric score
        text reason
        timestamptz created_at
    }

    brands {
        uuid id PK
        text name UK
        text normalized_name
    }

    categories {
        uuid id PK
        uuid parent_id FK
        text slug UK
        text name
    }

    products {
        uuid id PK
        uuid brand_id FK
        uuid category_id FK
        text model
        text name
        text sku
        text image_url
        jsonb attributes
        timestamptz created_at
        timestamptz updated_at
    }

    product_aliases {
        uuid id PK
        uuid product_id FK
        text source_name
        text alias
        text normalized_alias
    }

    product_variants {
        uuid id PK
        uuid product_id FK
        text size_value
        text size_system
        text color
        text sku
    }

    stores {
        uuid id PK
        text name UK
        text country
        text url
        boolean active
        boolean delivers_to_cz
        timestamptz created_at
    }

    source_configs {
        uuid id PK
        uuid store_id FK
        text source_type
        text endpoint_url
        boolean active
        jsonb settings
    }

    source_sync_runs {
        uuid id PK
        uuid store_id FK
        uuid source_config_id FK
        text source_type
        text status
        int products_seen
        int offers_seen
        text error_message
        timestamptz started_at
        timestamptz finished_at
    }

    source_product_mappings {
        uuid id PK
        uuid store_id FK
        uuid source_config_id FK
        text external_product_id
        uuid product_id FK
        jsonb raw_data
    }

    offers {
        uuid id PK
        uuid product_id FK
        uuid store_id FK
        text external_id
        text product_url
        numeric source_price
        numeric source_old_price
        text source_currency
        numeric eur_price
        numeric eur_old_price
        numeric fx_rate_to_eur
        numeric discount_percent
        text availability
        timestamptz last_seen_at
        timestamptz created_at
        timestamptz updated_at
    }

    offer_availability {
        uuid id PK
        uuid offer_id FK
        uuid variant_id FK
        boolean in_stock
        int stock_count
    }

    price_snapshots {
        uuid id PK
        uuid offer_id FK
        numeric source_price
        numeric source_old_price
        text source_currency
        numeric eur_price
        numeric eur_old_price
        numeric fx_rate_to_eur
        numeric discount_percent
        text availability
        timestamptz captured_at
    }

    price_analytics {
        uuid id PK
        uuid product_id FK
        uuid store_id FK
        numeric eur_min_30d
        numeric eur_min_90d
        numeric eur_min_180d
        numeric eur_min_365d
        numeric eur_min_all_time
        numeric eur_avg_365d
        timestamptz calculated_at
    }

    watchlists {
        uuid id PK
        uuid user_id FK
        text type
        uuid product_id FK
        uuid brand_id FK
        uuid category_id FK
        uuid source_request_id FK
        text model
        text size_value
        text size_system
        text color
        numeric target_price
        text target_price_currency
        numeric discount_threshold
        boolean notify_on_historical_min
        boolean active
        boolean archived
        timestamptz created_at
        timestamptz updated_at
    }

    watchlist_matches {
        uuid id PK
        uuid watchlist_id FK
        uuid offer_id FK
        text match_reason
        numeric score
        timestamptz matched_at
    }

    notifications {
        uuid id PK
        uuid user_id FK
        uuid watchlist_id FK
        uuid shopping_request_id FK
        uuid offer_id FK
        text type
        text status
        text message
        text dedupe_key
        timestamptz sent_at
        timestamptz created_at
    }
```

## Key API Resources

- Auth: Telegram login and token refresh.
- Shopping requests: natural-language shopping agent entry point.
- Recommendations: ranked products/offers for a request.
- Watchlists: long-running tracking rules created manually or after request confirmation.
- Products: normalized catalog.
- Offers: store-specific current prices and availability, including source currency and normalized EUR.
- Price history: historical snapshots and analytics.
- Deals: globally or personally relevant offers.
- Notifications: notification history.
- Admin: store/source/sync management.

## Confirmed Product Decisions

- Phase 1 uses a deterministic parser for shopping requests.
- Prices are stored in original source currency and normalized to EUR.
- A shopping request does not automatically create a watchlist; the user must confirm.

## Open Questions Before Implementation

- Which source should be integrated first: affiliate feed, Heureka, or one Playwright scraper?
- Do admins need a WebApp admin area in MVP, or backend endpoints are enough?
