from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.domains.catalog.models import Brand, Category, Product
from app.domains.offers.models import Offer, OfferAvailability, PriceSnapshot
from app.domains.stores.models import SourceConfig, SourceProductMapping, SourceSyncRun, Store
from app.domains.stores.sync import run_source_sync
from app.domains.users.models import User
from app.integrations.stores.base import SourceOfferRecord
from app.integrations.stores.fake import FakeStoreSourceAdapter


async def create_sync_fixture(db_session_factory: async_sessionmaker[AsyncSession]):
    async with db_session_factory() as session:
        admin = User(
            telegram_id=991,
            username="syncadmin",
            first_name="Sync",
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


def make_source_record(product: Product, *, eur_price: float) -> SourceOfferRecord:
    return SourceOfferRecord(
        external_id="footshop-nb-1080",
        product_id=product.id,
        product_url="https://www.footshop.cz/nb-1080",
        source_price=eur_price * 25,
        source_old_price=3990,
        source_currency="CZK",
        eur_price=eur_price,
        eur_old_price=159.60,
        fx_rate_to_eur=0.04,
        discount_percent=15.0,
        availability="in_stock",
        sizes=[
            {"size_value": "41", "size_system": "EU", "in_stock": True, "stock_count": 3},
            {"size_value": "42", "size_system": "EU", "in_stock": False},
        ],
    )


async def test_source_sync_creates_offer_run_and_price_snapshot(db_session_factory) -> None:
    _admin, product, store = await create_sync_fixture(db_session_factory)
    adapter = FakeStoreSourceAdapter([make_source_record(product, eur_price=139.60)])

    async with db_session_factory() as session:
        sync_run = await run_source_sync(session, adapter=adapter, store_id=store.id)
        await session.commit()

        assert sync_run.status == "succeeded"
        assert sync_run.products_seen == 1
        assert sync_run.offers_seen == 1

        offer_count = await session.scalar(select(func.count(Offer.id)))
        snapshot_count = await session.scalar(select(func.count(PriceSnapshot.id)))
        size_count = await session.scalar(select(func.count(OfferAvailability.id)))
        assert offer_count == 1
        assert snapshot_count == 1
        assert size_count == 2


async def test_source_sync_upserts_existing_external_offer(db_session_factory) -> None:
    _admin, product, store = await create_sync_fixture(db_session_factory)

    async with db_session_factory() as session:
        await run_source_sync(
            session,
            adapter=FakeStoreSourceAdapter([make_source_record(product, eur_price=139.60)]),
            store_id=store.id,
        )
        await run_source_sync(
            session,
            adapter=FakeStoreSourceAdapter([make_source_record(product, eur_price=129.90)]),
            store_id=store.id,
        )
        await session.commit()

        offer = await session.scalar(select(Offer).where(Offer.external_id == "footshop-nb-1080"))
        offer_count = await session.scalar(select(func.count(Offer.id)))
        snapshot_count = await session.scalar(select(func.count(PriceSnapshot.id)))
        sync_run_count = await session.scalar(select(func.count(SourceSyncRun.id)))

        assert offer is not None
        assert float(offer.eur_price) == 129.90
        assert offer_count == 1
        assert snapshot_count == 2
        assert sync_run_count == 2


async def test_admin_can_trigger_and_list_empty_fake_sync_run(
    client: TestClient,
    db_session_factory,
) -> None:
    admin, _product, store = await create_sync_fixture(db_session_factory)
    headers = {"Authorization": f"Bearer {create_access_token(str(admin.id))}"}

    response = client.post(
        "/v1/admin/sync-runs",
        headers=headers,
        json={"store_id": str(store.id), "source_type": "fake"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["store_id"] == str(store.id)
    assert body["offers_seen"] == 0

    list_response = client.get("/v1/admin/sync-runs", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == body["id"]


async def test_admin_rejects_unknown_sync_source(client: TestClient, db_session_factory) -> None:
    admin, _product, store = await create_sync_fixture(db_session_factory)
    headers = {"Authorization": f"Bearer {create_access_token(str(admin.id))}"}

    response = client.post(
        "/v1/admin/sync-runs",
        headers=headers,
        json={"store_id": str(store.id), "source_type": "unknown"},
    )

    assert response.status_code == 400


async def test_admin_can_manage_store_source_configs(
    client: TestClient,
    db_session_factory,
) -> None:
    admin, _product, store = await create_sync_fixture(db_session_factory)
    headers = {"Authorization": f"Bearer {create_access_token(str(admin.id))}"}

    create_response = client.post(
        f"/v1/admin/stores/{store.id}/source-configs",
        headers=headers,
        json={
            "source_type": "static_json",
            "endpoint_url": None,
            "active": True,
            "settings": {"records": []},
        },
    )
    assert create_response.status_code == 201
    source_config = create_response.json()
    assert source_config["store_id"] == str(store.id)
    assert source_config["source_type"] == "static_json"

    patch_response = client.patch(
        f"/v1/admin/source-configs/{source_config['id']}",
        headers=headers,
        json={"active": False},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["active"] is False

    list_response = client.get(
        f"/v1/admin/stores/{store.id}/source-configs",
        headers=headers,
    )
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == source_config["id"]


async def test_admin_can_run_static_json_source_config_sync(
    client: TestClient,
    db_session_factory,
) -> None:
    admin, product, store = await create_sync_fixture(db_session_factory)
    headers = {"Authorization": f"Bearer {create_access_token(str(admin.id))}"}

    create_response = client.post(
        f"/v1/admin/stores/{store.id}/source-configs",
        headers=headers,
        json={
            "source_type": "static_json",
            "active": True,
            "settings": {
                "records": [
                    {
                        "external_id": "static-json-nb-1080",
                        "product_id": str(product.id),
                        "product_url": "https://www.footshop.cz/nb-1080",
                        "source_price": 3190,
                        "source_old_price": 3990,
                        "source_currency": "CZK",
                        "eur_price": 127.60,
                        "eur_old_price": 159.60,
                        "fx_rate_to_eur": 0.04,
                        "discount_percent": 20.05,
                        "availability": "in_stock",
                        "sizes": [{"size_value": "41", "size_system": "EU", "in_stock": True}],
                    }
                ]
            },
        },
    )
    source_config_id = create_response.json()["id"]

    response = client.post(
        "/v1/admin/sync-runs",
        headers=headers,
        json={"source_config_id": source_config_id},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["store_id"] == str(store.id)
    assert body["source_config_id"] == source_config_id
    assert body["source_type"] == "static_json"
    assert body["products_seen"] == 1
    assert body["offers_seen"] == 1

    async with db_session_factory() as session:
        offer = await session.scalar(
            select(Offer).where(Offer.external_id == "static-json-nb-1080")
        )
        assert offer is not None
        assert float(offer.eur_price) == 127.60


async def test_static_json_sync_creates_product_and_mapping_from_source_data(
    client: TestClient,
    db_session_factory,
) -> None:
    admin, _product, store = await create_sync_fixture(db_session_factory)
    headers = {"Authorization": f"Bearer {create_access_token(str(admin.id))}"}

    create_response = client.post(
        f"/v1/admin/stores/{store.id}/source-configs",
        headers=headers,
        json={
            "source_type": "static_json",
            "active": True,
            "settings": {
                "records": [
                    {
                        "external_id": "static-json-asics-gt-2000-offer",
                        "product_url": "https://www.footshop.cz/asics-gt-2000",
                        "source_price": 2990,
                        "source_currency": "CZK",
                        "eur_price": 119.60,
                        "availability": "in_stock",
                        "sizes": [{"size_value": "41", "size_system": "EU", "in_stock": True}],
                        "product": {
                            "external_product_id": "asics-gt-2000",
                            "name": "ASICS GT-2000 13",
                            "brand_name": "ASICS",
                            "category_slug": "running-shoes",
                            "category_name": "Running Shoes",
                            "model": "GT-2000 13",
                            "sku": "ASICS-GT-2000-13",
                            "attributes": {"use_case": "daily training"},
                        },
                    }
                ]
            },
        },
    )
    source_config_id = create_response.json()["id"]

    for _ in range(2):
        response = client.post(
            "/v1/admin/sync-runs",
            headers=headers,
            json={"source_config_id": source_config_id},
        )
        assert response.status_code == 202
        body = response.json()
        assert body["error_message"] is None
        assert body["products_seen"] == 1

    async with db_session_factory() as session:
        product = await session.scalar(select(Product).where(Product.sku == "ASICS-GT-2000-13"))
        brand = await session.scalar(select(Brand).where(Brand.normalized_name == "asics"))
        mapping_count = await session.scalar(select(func.count(SourceProductMapping.id)))
        product_count = await session.scalar(
            select(func.count(Product.id)).where(Product.sku == "ASICS-GT-2000-13")
        )
        offer_count = await session.scalar(
            select(func.count(Offer.id)).where(
                Offer.external_id == "static-json-asics-gt-2000-offer"
            )
        )
        snapshot_count = await session.scalar(
            select(func.count(PriceSnapshot.id))
            .join(Offer, Offer.id == PriceSnapshot.offer_id)
            .where(Offer.external_id == "static-json-asics-gt-2000-offer")
        )

        assert product is not None
        assert product.name == "ASICS GT-2000 13"
        assert product.attributes == {"use_case": "daily training"}
        assert brand is not None
        assert mapping_count == 1
        assert product_count == 1
        assert offer_count == 1
        assert snapshot_count == 2


async def test_admin_rejects_inactive_source_config_sync(
    client: TestClient,
    db_session_factory,
) -> None:
    admin, _product, store = await create_sync_fixture(db_session_factory)
    headers = {"Authorization": f"Bearer {create_access_token(str(admin.id))}"}

    async with db_session_factory() as session:
        source_config = SourceConfig(
            store_id=store.id,
            source_type="static_json",
            active=False,
            settings={"records": []},
        )
        session.add(source_config)
        await session.commit()
        await session.refresh(source_config)
        source_config_id = source_config.id

    response = client.post(
        "/v1/admin/sync-runs",
        headers=headers,
        json={"source_config_id": str(source_config_id)},
    )

    assert response.status_code == 400
