from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.domains.catalog.models import Category, Product
from app.domains.shopping_requests.parser import parse_shopping_request
from app.domains.users.models import User


async def create_user_and_catalog(db_session_factory: async_sessionmaker[AsyncSession]) -> User:
    async with db_session_factory() as session:
        user = User(
            telegram_id=777,
            username="runner",
            first_name="Run",
            last_name=None,
            language="ru",
            country="CZ",
            currency="EUR",
            is_admin=False,
        )
        category = Category(slug="running-shoes", name="Running Shoes")
        session.add_all([user, category])
        await session.flush()
        session.add(
            Product(
                category_id=category.id,
                name="New Balance Fresh Foam 1080",
                model="Fresh Foam 1080",
                sku="NB-1080",
                attributes={"use_case": "daily training"},
            )
        )
        await session.commit()
        await session.refresh(user)
        return user


def test_deterministic_parser_extracts_running_shoe_constraints() -> None:
    parsed = parse_shopping_request(
        "Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро."
    )

    assert parsed.category == "running-shoes"
    assert parsed.use_case == "daily training"
    assert parsed.size_value == "41"
    assert parsed.size_system == "EU"
    assert parsed.max_price == 150
    assert parsed.max_price_currency == "EUR"
    assert parsed.attributes["parser"] == "deterministic-v1"


async def test_create_shopping_request_parses_constraints_and_recommends_product(
    client: TestClient,
    db_session_factory,
) -> None:
    user = await create_user_and_catalog(db_session_factory)
    token = create_access_token(str(user.id))

    response = client.post(
        "/v1/shopping-requests",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "text": (
                "Хочу беговые кроссовки для ежедневных тренировок. "
                "Размер 41. Бюджет 150 евро."
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "parsed"
    assert body["display_currency"] == "EUR"
    assert body["budget_amount"] == 150
    assert body["constraints"]["category"] == "running-shoes"
    assert body["constraints"]["size_value"] == "41"
    assert body["constraints"]["max_price_currency"] == "EUR"

    list_response = client.get(
        "/v1/shopping-requests",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    recommendations_response = client.get(
        f"/v1/shopping-requests/{body['id']}/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert recommendations_response.status_code == 200
    recommendations = recommendations_response.json()["items"]
    assert len(recommendations) == 1
    assert recommendations[0]["product"]["name"] == "New Balance Fresh Foam 1080"
    assert recommendations[0]["reason"] == "Matched by deterministic category parser."


async def test_user_cannot_read_other_users_shopping_request(
    client: TestClient,
    db_session_factory,
) -> None:
    first_user = await create_user_and_catalog(db_session_factory)
    first_token = create_access_token(str(first_user.id))
    create_response = client.post(
        "/v1/shopping-requests",
        headers={"Authorization": f"Bearer {first_token}"},
        json={"text": "Хочу кофе. Бюджет 20 евро."},
    )
    request_id = create_response.json()["id"]

    async with db_session_factory() as session:
        second_user = User(
            telegram_id=778,
            username="other",
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
        f"/v1/shopping-requests/{request_id}",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 404
