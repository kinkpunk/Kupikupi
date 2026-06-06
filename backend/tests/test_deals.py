from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.domains.catalog.models import Brand, Category, Product
from app.domains.offers.models import Offer, PriceAnalytics
from app.domains.stores.models import Store
from app.domains.users.models import User
from app.domains.watchlists.models import Watchlist


async def create_deals_fixture(db_session_factory: async_sessionmaker[AsyncSession]):
    async with db_session_factory() as session:
        user = User(
            telegram_id=1010,
            username="dealsuser",
            first_name="Deals",
            last_name=None,
            language="ru",
            country="CZ",
            currency="EUR",
            is_admin=False,
        )
        brand = Brand(name="New Balance", normalized_name="new balance")
        running = Category(slug="running-shoes", name="Running Shoes")
        coffee = Category(slug="coffee", name="Coffee")
        store = Store(name="Footshop", country="CZ", url="https://www.footshop.cz")
        session.add_all([user, brand, running, coffee, store])
        await session.flush()

        shoe = Product(
            brand_id=brand.id,
            category_id=running.id,
            name="New Balance Fresh Foam 1080",
            model="Fresh Foam 1080",
        )
        beans = Product(category_id=coffee.id, name="Coffee Beans")
        session.add_all([shoe, beans])
        await session.flush()

        shoe_offer = Offer(
            product_id=shoe.id,
            store_id=store.id,
            product_url="https://www.footshop.cz/nb-1080",
            source_price=3290,
            source_currency="CZK",
            eur_price=134.29,
            discount_percent=30,
            availability="in_stock",
        )
        coffee_offer = Offer(
            product_id=beans.id,
            store_id=store.id,
            product_url="https://www.footshop.cz/coffee",
            source_price=20,
            source_currency="EUR",
            eur_price=20,
            discount_percent=5,
            availability="in_stock",
        )
        session.add_all([shoe_offer, coffee_offer])
        await session.flush()

        session.add_all(
            [
                PriceAnalytics(
                    product_id=shoe.id,
                    store_id=store.id,
                    eur_min_all_time=134.29,
                    eur_lowest_10pct_365d_threshold=134.29,
                ),
                PriceAnalytics(
                    product_id=beans.id,
                    store_id=store.id,
                    eur_min_all_time=18,
                    eur_lowest_10pct_365d_threshold=18,
                ),
                Watchlist(
                    user_id=user.id,
                    type="category_rule",
                    category_id=running.id,
                    size_value="41",
                    target_price=150,
                    target_price_currency="EUR",
                    discount_threshold=20,
                    active=True,
                    archived=False,
                ),
            ]
        )
        await session.commit()
        await session.refresh(user)
        await session.refresh(running)
        return user, running


async def test_deals_rank_by_discount_and_analytics(client: TestClient, db_session_factory) -> None:
    user, _running = await create_deals_fixture(db_session_factory)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    response = client.get("/v1/deals", headers=headers, params={"personalized": False})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    first = body["items"][0]
    assert first["offer"]["eur_price"] == 134.29
    assert first["score"] > body["items"][1]["score"]
    assert "Historical minimum" in first["reasons"]
    assert "Lowest 10% of last 365 days" in first["reasons"]


async def test_personalized_deals_use_watchlists(client: TestClient, db_session_factory) -> None:
    user, _running = await create_deals_fixture(db_session_factory)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    response = client.get("/v1/deals", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    deal = body["items"][0]
    assert deal["offer"]["eur_price"] == 134.29
    assert "Matches watchlist" in deal["reasons"]
    assert "Target price reached" in deal["reasons"]
    assert "Discount threshold reached" in deal["reasons"]


async def test_deals_category_filter(client: TestClient, db_session_factory) -> None:
    user, _running = await create_deals_fixture(db_session_factory)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    response = client.get(
        "/v1/deals",
        headers=headers,
        params={"personalized": False, "category": "coffee"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["offer"]["eur_price"] == 20
