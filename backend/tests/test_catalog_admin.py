import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.domains.catalog.models import Brand, Category, Product
from app.domains.offers.models import Offer, PriceAnalytics
from app.domains.shopping_requests.models import Recommendation, ShoppingRequest
from app.domains.stores.models import (
    SourceConfig,
    SourceProductMapping,
    SourceSyncRun,
    SourceSyncRunItem,
    Store,
)
from app.domains.users.models import User
from app.domains.watchlists.models import Watchlist


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


async def test_admin_can_list_product_duplicate_candidates(
    client: TestClient,
    db_session_factory,
) -> None:
    admin = await create_test_user(db_session_factory, is_admin=True)
    token = create_access_token(str(admin.id))

    async with db_session_factory() as session:
        brand = Brand(name="ASICS", normalized_name="asics")
        category = Category(slug="running-shoes", name="Running Shoes")
        session.add_all([brand, category])
        await session.flush()
        session.add_all(
            [
                Product(
                    brand_id=brand.id,
                    category_id=category.id,
                    name="ASICS GT-2000 13",
                    model="GT-2000 13",
                    sku="ASICS-GT-2000-A",
                ),
                Product(
                    brand_id=brand.id,
                    category_id=category.id,
                    name="Asics GT 2000 13",
                    model="GT-2000 13",
                    sku="ASICS-GT-2000-B",
                ),
                Product(
                    brand_id=brand.id,
                    category_id=category.id,
                    name="ASICS Gel Nimbus",
                    model="Gel Nimbus",
                    sku="ASICS-NIMBUS",
                ),
            ]
        )
        await session.commit()

    response = client.get(
        "/v1/admin/product-duplicate-candidates",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    group = body["items"][0]
    assert group["normalized_identity"] == "gt-2000 13"
    assert len(group["products"]) == 2
    assert {product["sku"] for product in group["products"]} == {
        "ASICS-GT-2000-A",
        "ASICS-GT-2000-B",
    }


async def test_non_admin_cannot_list_product_duplicate_candidates(
    client: TestClient,
    db_session_factory,
) -> None:
    user = await create_test_user(db_session_factory, is_admin=False)
    token = create_access_token(str(user.id))

    response = client.get(
        "/v1/admin/product-duplicate-candidates",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


async def test_admin_can_merge_duplicate_product_references(
    client: TestClient,
    db_session_factory,
) -> None:
    admin = await create_test_user(db_session_factory, is_admin=True)
    token = create_access_token(str(admin.id))

    async with db_session_factory() as session:
        brand = Brand(name="ASICS", normalized_name="asics")
        category = Category(slug="running-shoes", name="Running Shoes")
        store = Store(name="Footshop", country="CZ", url="https://www.footshop.cz")
        session.add_all([brand, category, store])
        await session.flush()
        target = Product(
            brand_id=brand.id,
            category_id=category.id,
            name="ASICS GT-2000 13",
            model="GT-2000 13",
            sku="ASICS-GT-2000-A",
        )
        source = Product(
            brand_id=brand.id,
            category_id=category.id,
            name="Asics GT 2000 13",
            model="GT-2000 13",
            sku="ASICS-GT-2000-B",
        )
        session.add_all([target, source])
        await session.flush()
        source_config = SourceConfig(
            store_id=store.id,
            source_type="static_json",
            active=True,
            settings={},
        )
        request = ShoppingRequest(user_id=admin.id, raw_text="test", status="parsed")
        sync_run = SourceSyncRun(store_id=store.id, source_type="static_json", status="succeeded")
        session.add_all([source_config, request, sync_run])
        await session.flush()
        session.add_all(
            [
                Offer(
                    product_id=source.id,
                    store_id=store.id,
                    external_id="source-offer",
                    product_url="https://shop.example.test/source",
                    source_price=100,
                    source_currency="EUR",
                    eur_price=100,
                    availability="in_stock",
                ),
                PriceAnalytics(product_id=source.id),
                Recommendation(
                    request_id=request.id,
                    product_id=source.id,
                    score=50,
                    reason="duplicate",
                ),
                Watchlist(user_id=admin.id, type="product", product_id=source.id),
                SourceProductMapping(
                    store_id=store.id,
                    source_config_id=source_config.id,
                    external_product_id="source-product",
                    product_id=source.id,
                ),
                SourceSyncRunItem(
                    sync_run_id=sync_run.id,
                    external_id="source-offer",
                    status="succeeded",
                    product_id=source.id,
                ),
            ]
        )
        await session.commit()
        source_id = source.id
        target_id = target.id

    response = client.post(
        f"/v1/admin/products/{source_id}/merge",
        headers={"Authorization": f"Bearer {token}"},
        json={"target_product_id": str(target_id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_product_id"] == str(source_id)
    assert body["target_product_id"] == str(target_id)
    assert body["offers_moved"] == 1
    assert body["source_mappings_moved"] == 1
    assert body["sync_items_moved"] == 1

    async with db_session_factory() as session:
        assert await session.scalar(select(Product).where(Product.id == source_id)) is None
        assert (
            await session.scalar(select(func.count(Offer.id)).where(Offer.product_id == target_id))
            == 1
        )
        assert (
            await session.scalar(
                select(func.count(SourceProductMapping.id)).where(
                    SourceProductMapping.product_id == target_id
                )
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count(Watchlist.id)).where(Watchlist.product_id == target_id)
            )
            == 1
        )


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
