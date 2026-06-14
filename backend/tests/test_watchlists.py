from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.domains.catalog.models import Category
from app.domains.users.models import User


async def create_watchlist_user_and_category(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> tuple[User, Category]:
    async with db_session_factory() as session:
        user = User(
            telegram_id=880,
            username="watcher",
            first_name="Watch",
            last_name=None,
            language="ru",
            country="CZ",
            currency="EUR",
            is_admin=False,
        )
        category = Category(slug="running-shoes", name="Running Shoes")
        session.add_all([user, category])
        await session.commit()
        await session.refresh(user)
        await session.refresh(category)
        return user, category


async def test_watchlist_crud_pause_archive_delete(client: TestClient, db_session_factory) -> None:
    user, category = await create_watchlist_user_and_category(db_session_factory)
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/v1/watchlists",
        headers=headers,
        json={
            "type": "category_rule",
            "category_id": str(category.id),
            "size_value": "41",
            "size_system": "EU",
            "target_price": 150,
            "target_price_currency": "EUR",
        },
    )
    assert create_response.status_code == 201
    watchlist = create_response.json()
    assert watchlist["active"] is True
    assert watchlist["archived"] is False
    assert watchlist["category"] == "running-shoes"
    assert watchlist["brand"] is None
    assert watchlist["use_case"] is None

    list_response = client.get("/v1/watchlists", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    update_response = client.put(
        f"/v1/watchlists/{watchlist['id']}",
        headers=headers,
        json={"target_price": 120, "discount_threshold": 20},
    )
    assert update_response.status_code == 200
    assert update_response.json()["target_price"] == 120
    assert update_response.json()["discount_threshold"] == 20

    pause_response = client.post(f"/v1/watchlists/{watchlist['id']}/pause", headers=headers)
    assert pause_response.status_code == 200
    assert pause_response.json()["active"] is False

    archive_response = client.post(f"/v1/watchlists/{watchlist['id']}/archive", headers=headers)
    assert archive_response.status_code == 200
    assert archive_response.json()["archived"] is True

    archived_list_response = client.get("/v1/watchlists?archived=true", headers=headers)
    assert archived_list_response.status_code == 200
    assert archived_list_response.json()["total"] == 1

    restore_response = client.post(
        f"/v1/watchlists/{watchlist['id']}/restore",
        headers=headers,
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["active"] is True
    assert restore_response.json()["archived"] is False

    delete_response = client.delete(f"/v1/watchlists/{watchlist['id']}", headers=headers)
    assert delete_response.status_code == 204

    missing_response = client.get(f"/v1/watchlists/{watchlist['id']}", headers=headers)
    assert missing_response.status_code == 404


async def test_create_watchlist_from_shopping_request_requires_confirmation(
    client: TestClient,
    db_session_factory,
) -> None:
    user, category = await create_watchlist_user_and_category(db_session_factory)
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    request_response = client.post(
        "/v1/shopping-requests",
        headers=headers,
        json={
            "text": (
                "Хочу New Balance беговые кроссовки для ежедневных тренировок. "
                "Размер 41. Бюджет 150 евро."
            )
        },
    )
    assert request_response.status_code == 201
    request_id = request_response.json()["id"]

    before_confirmation = client.get("/v1/watchlists", headers=headers)
    assert before_confirmation.status_code == 200
    assert before_confirmation.json()["total"] == 0

    confirm_response = client.post(
        f"/v1/shopping-requests/{request_id}/watchlist",
        headers=headers,
    )
    assert confirm_response.status_code == 201
    watchlist = confirm_response.json()
    assert watchlist["type"] == "agent_request"
    assert watchlist["source_request_id"] == request_id
    assert watchlist["category_id"] == str(category.id)
    assert watchlist["category"] == "running-shoes"
    assert watchlist["brand"] == "New Balance"
    assert watchlist["use_case"] == "daily training"
    assert watchlist["size_value"] == "41"
    assert watchlist["target_price"] == 150
    assert watchlist["target_price_currency"] == "EUR"


async def test_user_cannot_read_other_users_watchlist(
    client: TestClient,
    db_session_factory,
) -> None:
    first_user, category = await create_watchlist_user_and_category(db_session_factory)
    first_token = create_access_token(str(first_user.id))
    create_response = client.post(
        "/v1/watchlists",
        headers={"Authorization": f"Bearer {first_token}"},
        json={"type": "category_rule", "category_id": str(category.id)},
    )
    watchlist_id = create_response.json()["id"]

    async with db_session_factory() as session:
        second_user = User(
            telegram_id=881,
            username="otherwatcher",
            first_name="Other",
            last_name=None,
            language="ru",
            country="CZ",
            currency="EUR",
            is_admin=False,
        )
        session.add(second_user)
        await session.commit()
        await session.refresh(second_user)

    second_token = create_access_token(str(second_user.id))
    response = client.get(
        f"/v1/watchlists/{watchlist_id}",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert response.status_code == 404
