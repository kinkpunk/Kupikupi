from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.models import Category
from app.domains.stores.models import Store

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


async def seed_mvp_data(session: AsyncSession) -> None:
    for slug, name in MVP_CATEGORIES:
        existing_category = await session.scalar(select(Category).where(Category.slug == slug))
        if existing_category is None:
            session.add(Category(slug=slug, name=name))

    for name, url in MVP_STORES:
        existing_store = await session.scalar(select(Store).where(Store.name == name))
        if existing_store is None:
            session.add(Store(name=name, country="CZ", url=url, active=True, delivers_to_cz=True))

    await session.commit()

