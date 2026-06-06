import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.catalog.models import Category, Product
from app.domains.deals.schemas import DealRead
from app.domains.offers.models import Offer
from app.domains.offers.service import attach_offer_flags
from app.domains.watchlists.models import Watchlist


async def list_deals(
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    category: str | None = None,
    personalized: bool = True,
    max_price_eur: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[DealRead], int]:
    query = (
        select(Offer, Product)
        .join(Product, Product.id == Offer.product_id)
        .options(selectinload(Offer.availability_items))
        .where(Offer.availability.in_(["in_stock", "limited"]))
    )

    if category:
        query = query.join(Category, Category.id == Product.category_id).where(
            Category.slug == category
        )

    if max_price_eur is not None:
        query = query.where(Offer.eur_price <= max_price_eur)

    watchlists = []
    if personalized and user_id is not None:
        watchlists = await _list_active_watchlists(session, user_id)
        if watchlists:
            query = query.where(_build_watchlist_filter(watchlists))

    rows = list((await session.execute(query)).all())
    deals = []
    for offer, product in rows:
        await attach_offer_flags(session, offer)
        deal = _build_deal(offer, product, watchlists)
        if deal.score > 0:
            deals.append(deal)

    deals.sort(key=lambda item: item.score, reverse=True)
    total = len(deals)
    return deals[offset : offset + limit], total


async def _list_active_watchlists(session: AsyncSession, user_id: uuid.UUID) -> list[Watchlist]:
    result = await session.execute(
        select(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.active.is_(True),
            Watchlist.archived.is_(False),
        )
    )
    return list(result.scalars().all())


def _build_watchlist_filter(watchlists: list[Watchlist]):
    filters = []
    for watchlist in watchlists:
        if watchlist.product_id is not None:
            filters.append(Offer.product_id == watchlist.product_id)
        if watchlist.category_id is not None:
            filters.append(Product.category_id == watchlist.category_id)
        if watchlist.brand_id is not None:
            filters.append(Product.brand_id == watchlist.brand_id)
    return or_(*filters) if filters else Offer.id.is_(None)


def _build_deal(offer: Offer, product: Product, watchlists: list[Watchlist]) -> DealRead:
    score = 0.0
    reasons = []

    discount = float(offer.discount_percent or 0)
    if discount > 0:
        score += min(discount, 60)
        reasons.append(f"Discount {discount:.0f}%")

    if getattr(offer, "is_historical_min", False):
        score += 35
        reasons.append("Historical minimum")

    if getattr(offer, "is_lowest_10_percent_365d", False):
        score += 25
        reasons.append("Lowest 10% of last 365 days")

    for watchlist in watchlists:
        if _matches_watchlist(offer, product, watchlist):
            score += 20
            reasons.append("Matches watchlist")
            if watchlist.target_price is not None and offer.eur_price <= watchlist.target_price:
                score += 30
                reasons.append("Target price reached")
            if (
                watchlist.discount_threshold is not None
                and offer.discount_percent is not None
                and offer.discount_percent >= watchlist.discount_threshold
            ):
                score += 20
                reasons.append("Discount threshold reached")
            break

    return DealRead(
        offer=offer,
        product_id=product.id,
        category_id=product.category_id,
        brand_id=product.brand_id,
        score=round(score, 2),
        reasons=reasons,
    )


def _matches_watchlist(offer: Offer, product: Product, watchlist: Watchlist) -> bool:
    if watchlist.product_id is not None and offer.product_id != watchlist.product_id:
        return False
    if watchlist.category_id is not None and product.category_id != watchlist.category_id:
        return False
    if watchlist.brand_id is not None and product.brand_id != watchlist.brand_id:
        return False
    return True
