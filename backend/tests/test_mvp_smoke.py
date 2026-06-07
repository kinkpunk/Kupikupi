from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.domains.catalog.models import Category, Product
from app.domains.stores.models import Store
from app.domains.users.models import User


async def create_smoke_fixture(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> tuple[User, User, Product, Store]:
    async with db_session_factory() as session:
        admin = User(
            telegram_id=3030,
            username="smokeadmin",
            first_name="Smoke",
            last_name=None,
            language="ru",
            country="CZ",
            currency="EUR",
            is_admin=True,
        )
        user = User(
            telegram_id=3031,
            username="smokeuser",
            first_name="Runner",
            last_name=None,
            language="ru",
            country="CZ",
            currency="EUR",
            is_admin=False,
        )
        category = Category(slug="running-shoes", name="Running Shoes")
        store = Store(name="Footshop", country="CZ", url="https://www.footshop.cz")
        session.add_all([admin, user, category, store])
        await session.flush()

        product = Product(
            category_id=category.id,
            name="New Balance Fresh Foam 1080",
            model="Fresh Foam 1080",
            sku="NB-1080",
            attributes={"use_case": "daily training"},
        )
        session.add(product)
        await session.commit()
        await session.refresh(admin)
        await session.refresh(user)
        await session.refresh(product)
        await session.refresh(store)
        return admin, user, product, store


async def test_mvp_user_shopping_flow_smoke(
    client: TestClient,
    db_session_factory,
) -> None:
    admin, user, product, store = await create_smoke_fixture(db_session_factory)
    admin_headers = {"Authorization": f"Bearer {create_access_token(str(admin.id))}"}
    user_headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    request_response = client.post(
        "/v1/shopping-requests",
        headers=user_headers,
        json={
            "text": (
                "Хочу беговые кроссовки для ежедневных тренировок. "
                "Размер 41. Бюджет 150 евро."
            )
        },
    )
    assert request_response.status_code == 201
    shopping_request = request_response.json()
    assert shopping_request["status"] == "parsed"
    assert shopping_request["constraints"]["category"] == "running-shoes"

    recommendations_response = client.get(
        f"/v1/shopping-requests/{shopping_request['id']}/recommendations",
        headers=user_headers,
    )
    assert recommendations_response.status_code == 200
    recommendations = recommendations_response.json()["items"]
    assert len(recommendations) == 1
    assert recommendations[0]["product"]["id"] == str(product.id)

    offer_response = client.post(
        "/v1/admin/offers",
        headers=admin_headers,
        json={
            "product_id": str(product.id),
            "store_id": str(store.id),
            "external_id": "smoke-footshop-nb-1080",
            "product_url": "https://www.footshop.cz/nb-1080",
            "source_price": 3290,
            "source_old_price": 4490,
            "source_currency": "CZK",
            "eur_price": 134.29,
            "eur_old_price": 183.27,
            "fx_rate_to_eur": 0.040817,
            "discount_percent": 30,
            "availability": "in_stock",
            "availability_items": [
                {"size_value": "41", "size_system": "EU", "in_stock": True, "stock_count": 2}
            ],
        },
    )
    assert offer_response.status_code == 201

    offers_response = client.get(
        f"/v1/products/{product.id}/offers",
        params={"size": "41", "in_stock": True},
    )
    assert offers_response.status_code == 200
    assert offers_response.json()["total"] == 1

    watchlist_response = client.post(
        f"/v1/shopping-requests/{shopping_request['id']}/watchlist",
        headers=user_headers,
    )
    assert watchlist_response.status_code == 201
    assert watchlist_response.json()["source_request_id"] == shopping_request["id"]

    deals_response = client.get("/v1/deals", headers=user_headers)
    assert deals_response.status_code == 200
    deals = deals_response.json()
    assert deals["total"] == 1
    assert deals["items"][0]["product_id"] == str(product.id)
    assert deals["items"][0]["offer"]["product_id"] == str(product.id)
    assert "Matches watchlist" in deals["items"][0]["reasons"]

    generate_response = client.post("/v1/admin/notifications/generate", headers=admin_headers)
    assert generate_response.status_code == 200
    assert generate_response.json()["created"] >= 1

    notifications_response = client.get("/v1/notifications", headers=user_headers)
    assert notifications_response.status_code == 200
    assert notifications_response.json()["total"] >= 1
