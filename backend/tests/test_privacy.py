from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.domains.catalog.models import Category, Product
from app.domains.notifications.models import Notification
from app.domains.privacy.service import count_user_data, delete_user_data, export_user_data
from app.domains.shopping_requests.models import (
    Recommendation,
    ShoppingRequest,
    ShoppingRequestConstraints,
)
from app.domains.users.models import User, UserSession
from app.domains.watchlists.models import Watchlist


async def test_export_user_data_returns_json_safe_payload_without_refresh_hash(
    db_session_factory,
) -> None:
    now = datetime(2026, 6, 7, tzinfo=UTC)

    async with db_session_factory() as session:
        user, request, product = await _create_user_data(session, now=now)
        await session.commit()

        payload = await export_user_data(session, telegram_id=user.telegram_id)

    assert payload is not None
    assert payload["user"]["telegram_id"] == 777000
    assert payload["summary"] == {
        "users": 1,
        "sessions": 1,
        "shopping_requests": 1,
        "shopping_request_constraints": 1,
        "recommendations": 1,
        "watchlists": 1,
        "notifications": 1,
    }
    assert payload["sessions"][0]["expires_at"] == (now + timedelta(days=30)).isoformat()
    assert "refresh_token_hash" not in payload["sessions"][0]
    assert payload["shopping_requests"][0]["id"] == str(request.id)
    assert payload["shopping_requests"][0]["constraints"]["size_value"] == "41"
    assert payload["shopping_requests"][0]["recommendations"][0]["product_id"] == str(product.id)
    assert payload["watchlists"][0]["size_value"] == "41"
    assert payload["notifications"][0]["dedupe_key"] == "privacy-test-notification"


async def test_delete_user_data_removes_user_owned_records_only(db_session_factory) -> None:
    now = datetime(2026, 6, 7, tzinfo=UTC)

    async with db_session_factory() as session:
        user, _, product = await _create_user_data(session, now=now)
        await session.commit()

        dry_run_stats = await count_user_data(session, telegram_id=user.telegram_id)

    assert dry_run_stats is not None
    assert dry_run_stats.as_dict()["users"] == 1

    async with db_session_factory() as session:
        stats = await delete_user_data(session, telegram_id=777000)
        await session.commit()

    assert stats is not None
    assert stats.as_dict() == {
        "users": 1,
        "sessions": 1,
        "shopping_requests": 1,
        "shopping_request_constraints": 1,
        "recommendations": 1,
        "watchlists": 1,
        "notifications": 1,
    }

    async with db_session_factory() as session:
        assert await session.scalar(select(func.count(User.id))) == 0
        assert await session.scalar(select(func.count(UserSession.id))) == 0
        assert await session.scalar(select(func.count(ShoppingRequest.id))) == 0
        assert await session.scalar(select(func.count(ShoppingRequestConstraints.id))) == 0
        assert await session.scalar(select(func.count(Recommendation.id))) == 0
        assert await session.scalar(select(func.count(Watchlist.id))) == 0
        assert await session.scalar(select(func.count(Notification.id))) == 0
        assert await session.scalar(select(func.count(Product.id))) == 1

        remaining_product = await session.scalar(select(Product).where(Product.id == product.id))

    assert remaining_product is not None


async def test_user_data_helpers_return_none_for_missing_user(db_session_factory) -> None:
    async with db_session_factory() as session:
        assert await export_user_data(session, telegram_id=404) is None
        assert await count_user_data(session, telegram_id=404) is None
        assert await delete_user_data(session, telegram_id=404) is None


async def _create_user_data(session, *, now: datetime) -> tuple[User, ShoppingRequest, Product]:
    category = Category(slug="running-shoes", name="Running Shoes")
    session.add(category)
    await session.flush()

    product = Product(
        category_id=category.id,
        name="New Balance Fresh Foam 1080",
        model="Fresh Foam 1080",
    )
    user = User(
        telegram_id=777000,
        username="privacy",
        first_name="Privacy",
        last_name="Tester",
        language="ru",
    )
    session.add_all([product, user])
    await session.flush()

    request = ShoppingRequest(
        user_id=user.id,
        raw_text="Хочу беговые кроссовки. Размер 41. Бюджет 150 евро.",
        status="confirmed",
        locale="ru",
        display_currency="EUR",
        budget_amount=150,
        created_at=now,
        updated_at=now,
    )
    session.add(request)
    await session.flush()

    session.add_all(
        [
            UserSession(
                user_id=user.id,
                refresh_token_hash="secret-refresh-token-hash",
                expires_at=now + timedelta(days=30),
                created_at=now,
            ),
            ShoppingRequestConstraints(
                request_id=request.id,
                category="running-shoes",
                use_case="daily training",
                size_value="41",
                size_system="EU",
                max_price=150,
                max_price_currency="EUR",
                attributes={"surface": "road"},
            ),
            Recommendation(
                request_id=request.id,
                product_id=product.id,
                score=0.95,
                reason="Matches daily training request",
                created_at=now,
            ),
            Watchlist(
                user_id=user.id,
                type="category",
                category_id=category.id,
                source_request_id=request.id,
                size_value="41",
                size_system="EU",
                target_price=150,
                target_price_currency="EUR",
                created_at=now,
                updated_at=now,
            ),
            Notification(
                user_id=user.id,
                shopping_request_id=request.id,
                type="deal",
                status="sent",
                message="Found a deal",
                dedupe_key="privacy-test-notification",
                sent_at=now,
                created_at=now,
            ),
        ]
    )
    await session.flush()
    return user, request, product
