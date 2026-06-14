from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.domains.catalog.models import Brand, Category, Product
from app.domains.offers.models import Offer, OfferAvailability
from app.domains.shopping_requests.parser import parse_shopping_request
from app.domains.stores.models import Store
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
        brand = Brand(name="New Balance", normalized_name="new balance")
        other_brand = Brand(name="Nike", normalized_name="nike")
        store = Store(name="Runner Shop", country="CZ", url="https://shop.example.test")
        session.add_all([user, category, brand, other_brand, store])
        await session.flush()
        matched_product = Product(
            brand_id=brand.id,
            category_id=category.id,
            name="New Balance Fresh Foam 1080",
            model="Fresh Foam 1080",
            sku="NB-1080",
            attributes={"use_case": "daily training"},
        )
        other_product = Product(
            brand_id=other_brand.id,
            category_id=category.id,
            name="Nike Pegasus Trail",
            model="Pegasus Trail",
            sku="NIKE-PEG-TRAIL",
            attributes={"use_case": "trail running"},
        )
        session.add_all([matched_product, other_product])
        await session.flush()
        matched_offer = Offer(
            product_id=matched_product.id,
            store_id=store.id,
            external_id="nb-1080",
            product_url="https://shop.example.test/nb-1080",
            source_price=3290,
            source_old_price=None,
            source_currency="CZK",
            eur_price=134.29,
            eur_old_price=None,
            fx_rate_to_eur=0.040817,
            discount_percent=None,
            availability="in_stock",
        )
        other_offer = Offer(
            product_id=other_product.id,
            store_id=store.id,
            external_id="nike-pegasus",
            product_url="https://shop.example.test/nike-pegasus",
            source_price=3990,
            source_old_price=None,
            source_currency="CZK",
            eur_price=162.84,
            eur_old_price=None,
            fx_rate_to_eur=0.040817,
            discount_percent=None,
            availability="in_stock",
        )
        session.add_all([matched_offer, other_offer])
        await session.flush()
        session.add_all(
            [
                OfferAvailability(
                    offer_id=matched_offer.id,
                    size_value="41",
                    size_system="EU",
                    in_stock=True,
                    stock_count=2,
                ),
                OfferAvailability(
                    offer_id=other_offer.id,
                    size_value="42",
                    size_system="EU",
                    in_stock=True,
                    stock_count=1,
                ),
            ]
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


def test_deterministic_parser_extracts_new_english_example() -> None:
    parsed = parse_shopping_request(
        "I need waterproof trail running shoes for muddy weekend runs, "
        "EU size 42, under 170 EUR."
    )

    assert parsed.category == "running-shoes"
    assert parsed.use_case == "trail running"
    assert parsed.size_value == "42"
    assert parsed.max_price == 170
    assert parsed.max_price_currency == "EUR"


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
    assert len(recommendations) == 2
    assert recommendations[0]["product"]["name"] == "New Balance Fresh Foam 1080"
    assert recommendations[0]["best_offer_id"] is not None
    assert recommendations[0]["score"] > recommendations[1]["score"]
    assert recommendations[0]["reason"] == (
        "Matched by category, use case, size in stock, within budget."
    )


async def test_recommendations_boost_preferred_brand_match(
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
                "Хочу New Balance беговые кроссовки для ежедневных тренировок. "
                "Размер 41. Бюджет 150 евро."
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["constraints"]["preferred_brand"] == "New Balance"

    recommendations_response = client.get(
        f"/v1/shopping-requests/{response.json()['id']}/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    recommendations = recommendations_response.json()["items"]

    assert recommendations[0]["product"]["name"] == "New Balance Fresh Foam 1080"
    assert recommendations[0]["reason"] == (
        "Matched by category, brand, model/text, use case, size in stock, within budget."
    )


async def test_user_can_edit_unconfirmed_shopping_request(
    client: TestClient,
    db_session_factory,
) -> None:
    user = await create_user_and_catalog(db_session_factory)
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    create_response = client.post(
        "/v1/shopping-requests",
        headers=headers,
        json={"text": "Хочу кофе. Бюджет 20 евро."},
    )
    request_id = create_response.json()["id"]

    update_response = client.put(
        f"/v1/shopping-requests/{request_id}",
        headers=headers,
        json={
            "text": (
                "Хочу New Balance беговые кроссовки для ежедневных тренировок. "
                "Размер 41. Бюджет 140 евро."
            )
        },
    )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["raw_text"].startswith("Хочу New Balance")
    assert body["budget_amount"] == 140
    assert body["constraints"]["category"] == "running-shoes"
    assert body["constraints"]["preferred_brand"] == "New Balance"

    recommendations_response = client.get(
        f"/v1/shopping-requests/{request_id}/recommendations",
        headers=headers,
    )
    recommendations = recommendations_response.json()["items"]
    assert len(recommendations) == 2
    assert recommendations[0]["product"]["name"] == "New Balance Fresh Foam 1080"


async def test_user_can_override_parsed_constraints(
    client: TestClient,
    db_session_factory,
) -> None:
    user = await create_user_and_catalog(db_session_factory)
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    create_response = client.post(
        "/v1/shopping-requests",
        headers=headers,
        json={"text": "Хочу кофе. Бюджет 20 евро."},
    )
    request_id = create_response.json()["id"]

    update_response = client.put(
        f"/v1/shopping-requests/{request_id}",
        headers=headers,
        json={
            "text": "Хочу кофе. Бюджет 20 евро.",
            "constraints": {
                "category": "running-shoes",
                "use_case": "trail running",
                "size_value": "42",
                "size_system": "EU",
                "preferred_brand": "Nike",
                "color": "green",
                "max_price": 175,
                "max_price_currency": "eur",
            },
        },
    )

    assert update_response.status_code == 200
    constraints = update_response.json()["constraints"]
    assert constraints["category"] == "running-shoes"
    assert constraints["use_case"] == "trail running"
    assert constraints["size_value"] == "42"
    assert constraints["preferred_brand"] == "Nike"
    assert constraints["color"] == "green"
    assert constraints["max_price"] == 175
    assert constraints["max_price_currency"] == "EUR"
    assert constraints["attributes"]["manual_override_fields"] == [
        "category",
        "color",
        "max_price",
        "max_price_currency",
        "preferred_brand",
        "size_system",
        "size_value",
        "use_case",
    ]


async def test_user_cannot_select_unknown_category(
    client: TestClient,
    db_session_factory,
) -> None:
    user = await create_user_and_catalog(db_session_factory)
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    create_response = client.post(
        "/v1/shopping-requests",
        headers=headers,
        json={"text": "Хочу кофе. Бюджет 20 евро."},
    )

    update_response = client.put(
        f"/v1/shopping-requests/{create_response.json()['id']}",
        headers=headers,
        json={
            "text": "Хочу кофе. Бюджет 20 евро.",
            "constraints": {"category": "unknown-category"},
        },
    )

    assert update_response.status_code == 422
    assert update_response.json()["detail"] == "Unknown shopping category."


async def test_confirmed_shopping_request_cannot_be_edited(
    client: TestClient,
    db_session_factory,
) -> None:
    user = await create_user_and_catalog(db_session_factory)
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    create_response = client.post(
        "/v1/shopping-requests",
        headers=headers,
        json={"text": "Хочу кроссовки. Размер 41. Бюджет 150 евро."},
    )
    request_id = create_response.json()["id"]
    confirm_response = client.post(
        f"/v1/shopping-requests/{request_id}/watchlist",
        headers=headers,
    )
    assert confirm_response.status_code == 201

    update_response = client.put(
        f"/v1/shopping-requests/{request_id}",
        headers=headers,
        json={"text": "Хочу кофе. Бюджет 20 евро."},
    )

    assert update_response.status_code == 409
    assert update_response.json()["detail"] == "Confirmed shopping requests cannot be edited."


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
