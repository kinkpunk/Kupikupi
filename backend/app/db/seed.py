from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.models import Category
from app.domains.fx.models import FxRate
from app.domains.stores.models import SourceConfig, Store

MVP_CATEGORIES = [
    ("sneakers", "Sneakers"),
    ("running-shoes", "Running Shoes"),
    ("clothing", "Clothing"),
    ("cosmetics", "Cosmetics"),
    ("coffee", "Coffee"),
]

MVP_STORES = [
    ("Footshop", "https://www.footshop.cz"),
    ("Queens", "https://www.queens.cz"),
    ("Zalando", "https://www.zalando.cz"),
    ("About You", "https://www.aboutyou.cz"),
    ("Sportisimo", "https://www.sportisimo.cz"),
    ("A3 Sport", "https://www.a3sport.cz"),
    ("11teamsports", "https://www.11teamsports.cz"),
    ("Notino", "https://www.notino.cz"),
    ("Dr. Max", "https://www.drmax.cz"),
    ("Pilulka", "https://www.pilulka.cz"),
    ("Rohlik", "https://www.rohlik.cz"),
    ("Kosik", "https://www.kosik.cz"),
]

MVP_DEMO_FX_RATES = [
    ("CZK", 0.040817, "seed", datetime(2026, 1, 1, tzinfo=UTC)),
]

MVP_DEMO_STATIC_JSON_RECORDS = [
    {
        "external_id": "demo-footshop-nb-1080",
        "product_url": "https://www.footshop.cz/demo/nb-1080",
        "source_price": 3290,
        "source_old_price": 4490,
        "source_currency": "CZK",
        "discount_percent": 26.73,
        "availability": "in_stock",
        "sizes": [
            {"size_value": "41", "size_system": "EU", "in_stock": True, "stock_count": 2},
            {"size_value": "42", "size_system": "EU", "in_stock": True, "stock_count": 1},
        ],
        "product": {
            "external_product_id": "demo-nb-1080",
            "name": "New Balance Fresh Foam 1080",
            "brand_name": "New Balance",
            "category_slug": "running-shoes",
            "category_name": "Running Shoes",
            "model": "Fresh Foam 1080",
            "sku": "DEMO-NB-1080",
            "attributes": {"use_case": "daily training"},
        },
    },
    {
        "external_id": "demo-footshop-asics-gt-2000",
        "product_url": "https://www.footshop.cz/demo/asics-gt-2000",
        "source_price": 2990,
        "source_old_price": 3690,
        "source_currency": "CZK",
        "discount_percent": 18.97,
        "availability": "limited",
        "sizes": [
            {"size_value": "41", "size_system": "EU", "in_stock": True, "stock_count": 1},
            {"size_value": "43", "size_system": "EU", "in_stock": False},
        ],
        "product": {
            "external_product_id": "demo-asics-gt-2000",
            "name": "ASICS GT-2000 13",
            "brand_name": "ASICS",
            "category_slug": "running-shoes",
            "category_name": "Running Shoes",
            "model": "GT-2000 13",
            "sku": "DEMO-ASICS-GT-2000-13",
            "attributes": {"use_case": "daily training"},
        },
    },
]


async def seed_mvp_data(session: AsyncSession) -> None:
    for slug, name in MVP_CATEGORIES:
        existing_category = await session.scalar(select(Category).where(Category.slug == slug))
        if existing_category is None:
            session.add(Category(slug=slug, name=name))

    for name, url in MVP_STORES:
        existing_store = await session.scalar(select(Store).where(Store.name == name))
        if existing_store is None:
            session.add(Store(name=name, country="CZ", url=url, active=True, delivers_to_cz=True))

    await session.flush()
    await _seed_demo_fx_rates(session)
    await _seed_demo_source_config(session)
    await session.commit()


async def _seed_demo_fx_rates(session: AsyncSession) -> None:
    for currency, rate_to_eur, source, valid_at in MVP_DEMO_FX_RATES:
        existing_rate = await session.scalar(
            select(FxRate).where(FxRate.currency == currency, FxRate.valid_at == valid_at)
        )
        if existing_rate is None:
            session.add(
                FxRate(
                    currency=currency,
                    rate_to_eur=rate_to_eur,
                    source=source,
                    valid_at=valid_at,
                )
            )


async def _seed_demo_source_config(session: AsyncSession) -> None:
    footshop = await session.scalar(select(Store).where(Store.name == "Footshop"))
    if footshop is None:
        return

    settings = {
        "demo": True,
        "records": MVP_DEMO_STATIC_JSON_RECORDS,
    }
    source_config = await session.scalar(
        select(SourceConfig).where(
            SourceConfig.store_id == footshop.id,
            SourceConfig.source_type == "static_json",
            SourceConfig.settings["demo"].as_boolean().is_(True),
        )
    )
    if source_config is None:
        session.add(
            SourceConfig(
                store_id=footshop.id,
                source_type="static_json",
                active=True,
                sync_interval_minutes=60,
                next_sync_at=datetime.now(UTC),
                settings=settings,
            )
        )
        return

    source_config.active = True
    source_config.sync_interval_minutes = 60
    source_config.settings = settings
