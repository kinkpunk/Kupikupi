import uuid

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.domains.catalog.models import Category
from app.domains.users.models import User


async def create_test_user(
    db_session_factory: async_sessionmaker[AsyncSession],
    *,
    is_admin: bool,
) -> User:
    async with db_session_factory() as session:
        user = User(
            telegram_id=9000 + int(is_admin),
            username="admin" if is_admin else "user",
            first_name="Test",
            last_name=None,
            language="ru",
            country="CZ",
            currency="EUR",
            is_admin=is_admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def test_admin_can_create_store(client: TestClient, db_session_factory) -> None:
    admin = await create_test_user(db_session_factory, is_admin=True)
    token = create_access_token(str(admin.id))

    response = client.post(
        "/v1/admin/stores",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Footshop",
            "country": "CZ",
            "url": "https://www.footshop.cz",
            "active": True,
            "delivers_to_cz": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Footshop"
    assert body["delivers_to_cz"] is True

    list_response = client.get("/v1/admin/stores", headers={"Authorization": f"Bearer {token}"})
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["name"] == "Footshop"


async def test_non_admin_cannot_create_store(client: TestClient, db_session_factory) -> None:
    user = await create_test_user(db_session_factory, is_admin=False)
    token = create_access_token(str(user.id))

    response = client.post(
        "/v1/admin/stores",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Queens", "url": "https://www.queens.cz"},
    )

    assert response.status_code == 403


async def test_admin_can_create_catalog_and_public_search(
    client: TestClient,
    db_session_factory,
) -> None:
    admin = await create_test_user(db_session_factory, is_admin=True)
    token = create_access_token(str(admin.id))
    headers = {"Authorization": f"Bearer {token}"}

    brand_response = client.post("/v1/admin/brands", headers=headers, json={"name": "New Balance"})
    assert brand_response.status_code == 201
    brand_id = brand_response.json()["id"]

    category_response = client.post(
        "/v1/admin/categories",
        headers=headers,
        json={"slug": "running-shoes", "name": "Running Shoes"},
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    product_response = client.post(
        "/v1/admin/products",
        headers=headers,
        json={
            "brand_id": brand_id,
            "category_id": category_id,
            "model": "Fresh Foam 1080",
            "name": "New Balance Fresh Foam 1080",
            "sku": "NB-1080",
            "attributes": {"use_case": "daily training"},
        },
    )
    assert product_response.status_code == 201

    search_response = client.get("/v1/products", params={"q": "fresh foam"})
    assert search_response.status_code == 200
    body = search_response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "New Balance Fresh Foam 1080"


async def test_product_detail_returns_404_for_missing_product(client: TestClient) -> None:
    response = client.get(f"/v1/products/{uuid.uuid4()}")

    assert response.status_code == 404


async def test_categories_are_public(client: TestClient, db_session_factory) -> None:
    async with db_session_factory() as session:
        session.add(Category(slug="coffee", name="Coffee"))
        await session.commit()

    response = client.get("/v1/categories")

    assert response.status_code == 200
    assert response.json()[0]["slug"] == "coffee"
