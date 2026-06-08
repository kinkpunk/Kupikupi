import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.catalog.models import Category, Product
from app.domains.offers.models import Offer, OfferAvailability
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
        .options(selectinload(Product.brand))
        .where(Category.slug == parsed.category)
    )
    products = list((await session.execute(products_query)).scalars().all())
    offers_by_product_id = await _offers_by_product_id(
        session,
        product_ids=[p.id for p in products],
    )

    scored_products = [
        _score_product(product, parsed, offers_by_product_id.get(product.id, []))
        for product in products
    ]
    scored_products.sort(key=lambda item: item[1], reverse=True)

    for product, score, reason, best_offer_id in scored_products[:5]:
        session.add(
            Recommendation(
                request_id=request.id,
                product_id=product.id,
                best_offer_id=best_offer_id,
                score=score,
                reason=reason,
            )
        )


async def _offers_by_product_id(
    session: AsyncSession,
    *,
    product_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[Offer]]:
    if not product_ids:
        return {}
    result = await session.execute(
        select(Offer)
        .options(selectinload(Offer.availability_items))
        .where(Offer.product_id.in_(product_ids))
        .order_by(Offer.eur_price.asc())
    )
    offers_by_product_id: dict[uuid.UUID, list[Offer]] = {}
    for offer in result.scalars().all():
        offers_by_product_id.setdefault(offer.product_id, []).append(offer)
    return offers_by_product_id


def _score_product(
    product: Product,
    parsed: ParsedShoppingRequest,
    offers: list[Offer],
) -> tuple[Product, float, str, uuid.UUID | None]:
    score = 50.0
    reasons = ["category"]

    if parsed.preferred_brand and _product_brand_matches(product, parsed.preferred_brand):
        score += 25
        reasons.append("brand")

    if _text_matches_product(product, parsed):
        score += 15
        reasons.append("model/text")

    if parsed.use_case and _product_use_case_matches(product, parsed.use_case):
        score += 10
        reasons.append("use case")

    best_offer = _best_offer(offers)
    if parsed.size_value and _has_size_offer(offers, parsed):
        score += 10
        reasons.append("size in stock")

    if best_offer is not None and parsed.max_price and parsed.max_price_currency == "EUR":
        if float(best_offer.eur_price) <= parsed.max_price:
            score += 10
            reasons.append("within budget")

    return product, round(score, 2), "Matched by " + ", ".join(reasons) + ".", _offer_id(best_offer)


def _product_brand_matches(product: Product, preferred_brand: str) -> bool:
    brand_name = product.brand.name if product.brand else ""
    brand = _normalize(preferred_brand)
    return brand == _normalize(brand_name) or brand in _normalize(product.name)


def _text_matches_product(product: Product, parsed: ParsedShoppingRequest) -> bool:
    searchable = _normalize(" ".join([product.name, product.model or "", product.sku or ""]))
    request_terms = [
        term
        for term in [_normalize(parsed.preferred_brand or ""), _normalize(parsed.use_case or "")]
        if term
    ]
    return any(term and term in searchable for term in request_terms)


def _product_use_case_matches(product: Product, use_case: str) -> bool:
    attributes = product.attributes or {}
    value = attributes.get("use_case")
    if isinstance(value, str):
        return _normalize(use_case) in _normalize(value)
    if isinstance(value, list):
        return any(_normalize(use_case) in _normalize(str(item)) for item in value)
    return False


def _has_size_offer(offers: list[Offer], parsed: ParsedShoppingRequest) -> bool:
    for offer in offers:
        for item in offer.availability_items:
            if _availability_matches_size(item, parsed):
                return True
    return False


def _availability_matches_size(
    item: OfferAvailability,
    parsed: ParsedShoppingRequest,
) -> bool:
    if not item.in_stock:
        return False
    if parsed.size_value and item.size_value != parsed.size_value:
        return False
    if parsed.size_system and item.size_system and item.size_system != parsed.size_system:
        return False
    return True


def _best_offer(offers: list[Offer]) -> Offer | None:
    in_stock_offers = [offer for offer in offers if offer.availability == "in_stock"]
    candidates = in_stock_offers or offers
    if not candidates:
        return None
    return min(candidates, key=lambda offer: float(offer.eur_price))


def _offer_id(offer: Offer | None) -> uuid.UUID | None:
    return offer.id if offer is not None else None


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())
