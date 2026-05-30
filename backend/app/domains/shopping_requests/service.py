import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.catalog.models import Category, Product
from app.domains.shopping_requests.models import (
    Recommendation,
    ShoppingRequest,
    ShoppingRequestConstraints,
)
from app.domains.shopping_requests.parser import ParsedShoppingRequest, parse_shopping_request
from app.domains.users.models import User


async def create_shopping_request(
    session: AsyncSession,
    *,
    user: User,
    raw_text: str,
) -> ShoppingRequest:
    parsed = parse_shopping_request(raw_text)
    request = ShoppingRequest(
        user_id=user.id,
        raw_text=raw_text,
        status="parsed",
        locale=user.language,
        display_currency=parsed.max_price_currency or user.currency,
        budget_amount=parsed.max_price,
    )
    request.constraints = _build_constraints(parsed)
    session.add(request)
    await session.flush()

    await _create_recommendation_drafts(session, request, parsed)
    await session.flush()
    return await get_shopping_request(session, user_id=user.id, request_id=request.id) or request


async def list_shopping_requests(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int,
    offset: int,
) -> tuple[list[ShoppingRequest], int]:
    total_result = await session.execute(
        select(func.count(ShoppingRequest.id)).where(ShoppingRequest.user_id == user_id)
    )
    result = await session.execute(
        select(ShoppingRequest)
        .options(selectinload(ShoppingRequest.constraints))
        .where(ShoppingRequest.user_id == user_id)
        .order_by(ShoppingRequest.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total_result.scalar_one()


async def get_shopping_request(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    request_id: uuid.UUID,
) -> ShoppingRequest | None:
    result = await session.execute(
        select(ShoppingRequest)
        .options(selectinload(ShoppingRequest.constraints))
        .where(ShoppingRequest.id == request_id, ShoppingRequest.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_recommendations(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    request_id: uuid.UUID,
) -> list[Recommendation]:
    result = await session.execute(
        select(Recommendation)
        .join(ShoppingRequest, ShoppingRequest.id == Recommendation.request_id)
        .options(selectinload(Recommendation.product))
        .where(Recommendation.request_id == request_id, ShoppingRequest.user_id == user_id)
        .order_by(Recommendation.score.desc())
    )
    return list(result.scalars().all())


def _build_constraints(parsed: ParsedShoppingRequest) -> ShoppingRequestConstraints:
    return ShoppingRequestConstraints(
        category=parsed.category,
        use_case=parsed.use_case,
        size_value=parsed.size_value,
        size_system=parsed.size_system,
        preferred_brand=parsed.preferred_brand,
        color=parsed.color,
        max_price=parsed.max_price,
        max_price_currency=parsed.max_price_currency,
        attributes=parsed.attributes,
    )


async def _create_recommendation_drafts(
    session: AsyncSession,
    request: ShoppingRequest,
    parsed: ParsedShoppingRequest,
) -> None:
    if not parsed.category:
        return

    products_query = (
        select(Product)
        .join(Category, Category.id == Product.category_id)
        .where(Category.slug == parsed.category)
        .limit(5)
    )
    products = list((await session.execute(products_query)).scalars().all())

    for product in products:
        session.add(
            Recommendation(
                request_id=request.id,
                product_id=product.id,
                score=50.0,
                reason="Matched by deterministic category parser.",
            )
        )

