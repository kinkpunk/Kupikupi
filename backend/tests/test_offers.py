from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.domains.catalog.models import Category, Product
from app.domains.stores.models import Store
from app.domains.users.models import User


async def create_offer_fixture(db_session_factory: async_sessionmaker[AsyncSession]):
    async with db_session_factory() as session:
        admin = User(
            telegram_id=990,
            username="offeradmin",
            first_name="Offer",
            last_name=None,
            language="ru",
            country="CZ",
            currency="EUR",
            is_admin=True,
        )
        category = Category(slug="running-shoes", name="Running Shoes")
        store = Store(name="Footshop", country="CZ", url="https://www.footshop.cz")
        session.add_all([admin, category, store])
        await session.flush()
        product = Product(
            category_id=category.id,
            name="New Balance Fresh Foam 1080",
            model="Fresh Foam 1080",
            sku="NB-1080",
        )
        session.add(product)
        await session.commit()
        await session.refresh(admin)
        await session.refresh(product)
        await session.refresh(store)
        return admin, product, store


async def test_admin_creates_offer_and_price_history(
    client: TestClient,
    db_session_factory,
) -> None:
    admin, product, store = await create_offer_fixture(db_session_factory)
    headers = {"Authorization": f"Bearer {create_access_token(str(admin.id))}"}

    create_response = client.post(
        "/v1/admin/offers",
        headers=headers,
        json={
            "product_id": str(product.id),
            "store_id": str(store.id),
            "external_id": "footshop-nb-1080",
            "product_url": "https://www.footshop.cz/nb-1080",
            "source_price": 3490,
            "source_old_price": 4490,
            "source_currency": "CZK",
            "eur_price": 142.45,
            "eur_old_price": 183.27,
            "fx_rate_to_eur": 0.040817,
            "discount_percent": 22.27,
            "availability": "in_stock",
            "availability_items": [
                {"size_value": "41", "size_system": "EU", "in_stock": True, "stock_count": 2},
                {"size_value": "42", "size_system": "EU", "in_stock": False},
            ],
        },
    )
    assert create_response.status_code == 201
    offer = create_response.json()
    assert offer["source_currency"] == "CZK"
    assert offer["eur_price"] == 142.45
    assert len(offer["availability_items"]) == 2

    offers_response = client.get(f"/v1/products/{product.id}/offers", params={"size": "41"})
    assert offers_response.status_code == 200
    assert offers_response.json()["total"] == 1

    update_response = client.patch(
        f"/v1/admin/offers/{offer['id']}",
        headers=headers,
        json={"source_price": 3290, "eur_price": 134.29, "discount_percent": 26.73},
    )
    assert update_response.status_code == 200
    assert update_response.json()["eur_price"] == 134.29

    history_response = client.get(f"/v1/price-history/{product.id}")
    assert history_response.status_code == 200
    history = history_response.json()
    assert history["product_id"] == str(product.id)
    assert len(history["points"]) == 2
    assert history["points"][0]["eur_price"] == 142.45
    assert history["points"][1]["eur_price"] == 134.29


async def test_offer_filter_can_require_in_stock_size(
    client: TestClient,
    db_session_factory,
) -> None:
    admin, product, store = await create_offer_fixture(db_session_factory)
    headers = {"Authorization": f"Bearer {create_access_token(str(admin.id))}"}
    client.post(
        "/v1/admin/offers",
        headers=headers,
        json={
            "product_id": str(product.id),
            "store_id": str(store.id),
            "product_url": "https://www.footshop.cz/nb-1080",
            "source_price": 3490,
            "source_currency": "CZK",
            "eur_price": 142.45,
            "availability": "in_stock",
            "availability_items": [
                {"size_value": "42", "size_system": "EU", "in_stock": False},
            ],
        },
    )

    response = client.get(
        f"/v1/products/{product.id}/offers",
        params={"size": "42", "in_stock": True},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
