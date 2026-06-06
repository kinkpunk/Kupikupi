from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.domains.catalog.models import Category, Product
from app.domains.notifications.service import dispatch_created_notifications, generate_notifications
from app.domains.offers.models import Offer, PriceAnalytics
from app.domains.stores.models import Store
from app.domains.users.models import User
from app.domains.watchlists.models import Watchlist
from app.integrations.telegram.client import TelegramDeliveryError


class FakeTelegramClient:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, *, chat_id: int, text: str) -> None:
        if self.should_fail:
            raise TelegramDeliveryError("boom")
        self.messages.append((chat_id, text))


async def create_notification_fixture(db_session_factory: async_sessionmaker[AsyncSession]):
    async with db_session_factory() as session:
        admin = User(
            telegram_id=2020,
            username="notifyadmin",
            first_name="Admin",
            last_name=None,
            language="ru",
            country="CZ",
            currency="EUR",
            is_admin=True,
        )
        user = User(
            telegram_id=2021,
            username="notifyuser",
            first_name="User",
            last_name=None,
            language="ru",
            country="CZ",
            currency="EUR",
            is_admin=False,
        )
        other_user = User(
            telegram_id=2022,
            username="othernotify",
            first_name="Other",
            last_name=None,
            language="ru",
            country="CZ",
            currency="EUR",
            is_admin=False,
        )
        category = Category(slug="running-shoes", name="Running Shoes")
        store = Store(name="Footshop", country="CZ", url="https://www.footshop.cz")
        session.add_all([admin, user, other_user, category, store])
        await session.flush()

        product = Product(category_id=category.id, name="New Balance Fresh Foam 1080")
        session.add(product)
        await session.flush()

        offer = Offer(
            product_id=product.id,
            store_id=store.id,
            product_url="https://www.footshop.cz/nb-1080",
            source_price=3290,
            source_currency="CZK",
            eur_price=134.29,
            discount_percent=30,
            availability="in_stock",
        )
        session.add(offer)
        await session.flush()

        session.add_all(
            [
                PriceAnalytics(
                    product_id=product.id,
                    store_id=store.id,
                    eur_min_all_time=134.29,
                    eur_lowest_10pct_365d_threshold=134.29,
                ),
                Watchlist(
                    user_id=user.id,
                    type="category_rule",
                    category_id=category.id,
                    target_price=150,
                    target_price_currency="EUR",
                    discount_threshold=20,
                    notify_on_historical_min=True,
                    active=True,
                    archived=False,
                ),
            ]
        )
        await session.commit()
        await session.refresh(admin)
        await session.refresh(user)
        await session.refresh(other_user)
        return admin, user, other_user


async def test_admin_generates_notifications_with_dedupe(
    client: TestClient,
    db_session_factory,
) -> None:
    admin, user, _other_user = await create_notification_fixture(db_session_factory)
    admin_headers = {"Authorization": f"Bearer {create_access_token(str(admin.id))}"}
    user_headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    first_response = client.post("/v1/admin/notifications/generate", headers=admin_headers)

    assert first_response.status_code == 200
    assert first_response.json() == {"created": 4, "skipped": 0}

    second_response = client.post("/v1/admin/notifications/generate", headers=admin_headers)
    assert second_response.status_code == 200
    assert second_response.json() == {"created": 0, "skipped": 4}

    list_response = client.get("/v1/notifications", headers=user_headers)
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 4
    notification_types = {item["type"] for item in body["items"]}
    assert notification_types == {
        "target_price",
        "discount",
        "historical_min",
        "lowest_10_percent_365d",
    }


async def test_user_only_sees_own_notifications(client: TestClient, db_session_factory) -> None:
    admin, user, other_user = await create_notification_fixture(db_session_factory)
    admin_headers = {"Authorization": f"Bearer {create_access_token(str(admin.id))}"}
    other_headers = {"Authorization": f"Bearer {create_access_token(str(other_user.id))}"}
    user_headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    client.post("/v1/admin/notifications/generate", headers=admin_headers)

    user_response = client.get("/v1/notifications", headers=user_headers)
    other_response = client.get("/v1/notifications", headers=other_headers)

    assert user_response.status_code == 200
    assert user_response.json()["total"] == 4
    assert other_response.status_code == 200
    assert other_response.json()["total"] == 0


async def test_dispatch_created_notifications_marks_sent(db_session_factory) -> None:
    _admin, user, _other_user = await create_notification_fixture(db_session_factory)
    fake_client = FakeTelegramClient()

    async with db_session_factory() as session:
        generation = await generate_notifications(session)
        assert generation.created == 4

        dispatch = await dispatch_created_notifications(session, telegram_client=fake_client)
        await session.commit()

    assert dispatch.sent == 4
    assert dispatch.failed == 0
    assert len(fake_client.messages) == 4
    assert {chat_id for chat_id, _text in fake_client.messages} == {user.telegram_id}


async def test_dispatch_created_notifications_marks_failed(db_session_factory) -> None:
    await create_notification_fixture(db_session_factory)

    async with db_session_factory() as session:
        generation = await generate_notifications(session)
        assert generation.created == 4

        dispatch = await dispatch_created_notifications(
            session,
            telegram_client=FakeTelegramClient(should_fail=True),
        )
        await session.commit()

    assert dispatch.sent == 0
    assert dispatch.failed == 4
