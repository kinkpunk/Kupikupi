from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.domains.catalog.models import Category, Product
from app.domains.offers.models import Offer, OfferAvailability, PriceSnapshot
from app.domains.stores.models import SourceSyncRun, Store
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
