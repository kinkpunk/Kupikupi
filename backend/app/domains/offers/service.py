import uuid
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.offers.models import Offer, OfferAvailability, PriceAnalytics, PriceSnapshot
from app.domains.offers.schemas import OfferCreate, OfferUpdate

PERIOD_DAYS = {
    "30d": 30,
    "90d": 90,
    "180d": 180,
    "365d": 365,
}


async def create_offer(session: AsyncSession, payload: OfferCreate) -> Offer:
    data = payload.model_dump(exclude={"availability_items"})
    offer = Offer(**data)
    offer.availability_items = [
        OfferAvailability(**item.model_dump()) for item in payload.availability_items
    ]
    session.add(offer)
    await session.flush()
    await create_price_snapshot(session, offer)
    await recompute_offer_analytics(session, offer)
    return offer


async def update_offer(session: AsyncSession, offer: Offer, payload: OfferUpdate) -> Offer:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(offer, field, value)
    await session.flush()
    await create_price_snapshot(session, offer)
    await recompute_offer_analytics(session, offer)
    return offer


async def create_price_snapshot(session: AsyncSession, offer: Offer) -> PriceSnapshot:
    snapshot = PriceSnapshot(
        offer_id=offer.id,
        source_price=offer.source_price,
        source_old_price=offer.source_old_price,
        source_currency=offer.source_currency,
        eur_price=offer.eur_price,
        eur_old_price=offer.eur_old_price,
        fx_rate_to_eur=offer.fx_rate_to_eur,
        discount_percent=offer.discount_percent,
        availability=offer.availability,
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


async def get_offer(session: AsyncSession, offer_id: uuid.UUID) -> Offer | None:
    offer = await session.scalar(
        select(Offer)
        .options(selectinload(Offer.availability_items))
        .where(Offer.id == offer_id)
    )
    if offer is not None:
        await attach_offer_flags(session, offer)
    return offer


async def list_product_offers(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    in_stock: bool | None = None,
    size: str | None = None,
) -> tuple[list[Offer], int]:
    query = select(Offer).options(selectinload(Offer.availability_items))
    count_query = select(func.count(Offer.id))
    filters = [Offer.product_id == product_id]

    if in_stock is not None or size is not None:
        query = query.join(OfferAvailability)
        count_query = count_query.join(OfferAvailability)
        if in_stock is not None:
            filters.append(OfferAvailability.in_stock == in_stock)
        if size is not None:
            filters.append(OfferAvailability.size_value == size)

    query = query.where(*filters).order_by(Offer.eur_price.asc())
    count_query = count_query.where(*filters)

    total = (await session.execute(count_query)).scalar_one()
    offers = list((await session.execute(query)).scalars().unique().all())
    for offer in offers:
        await attach_offer_flags(session, offer)
    return offers, total


async def list_product_price_points(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    period: str = "90d",
) -> list[tuple[PriceSnapshot, uuid.UUID]]:
    filters = [Offer.product_id == product_id]
    if period != "all":
        cutoff = datetime.now(UTC) - timedelta(days=PERIOD_DAYS[period])
        filters.append(PriceSnapshot.captured_at >= cutoff)

    result = await session.execute(
        select(PriceSnapshot, Offer.store_id)
        .join(Offer, Offer.id == PriceSnapshot.offer_id)
        .where(*filters)
        .order_by(PriceSnapshot.captured_at.asc())
    )
    return list(result.all())


async def recompute_offer_analytics(session: AsyncSession, offer: Offer) -> None:
    await compute_price_analytics(session, product_id=offer.product_id, store_id=None)
    await compute_price_analytics(session, product_id=offer.product_id, store_id=offer.store_id)


async def compute_price_analytics(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    store_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> PriceAnalytics:
    now = now or datetime.now(UTC)
    filters = [Offer.product_id == product_id]
    if store_id is None:
        filters.append(Offer.store_id.is_not(None))
    else:
        filters.append(Offer.store_id == store_id)

    result = await session.execute(
        select(PriceSnapshot)
        .join(Offer, Offer.id == PriceSnapshot.offer_id)
        .where(*filters)
        .order_by(PriceSnapshot.captured_at.asc())
    )
    snapshots = list(result.scalars().all())
    prices = [
        (float(snapshot.eur_price), _ensure_aware(snapshot.captured_at))
        for snapshot in snapshots
    ]

    analytics = await get_price_analytics(session, product_id=product_id, store_id=store_id)
    if analytics is None:
        analytics = PriceAnalytics(product_id=product_id, store_id=store_id)
        session.add(analytics)

    all_prices = [price for price, _captured_at in prices]
    prices_365d = [
        price for price, captured_at in prices if captured_at >= now - timedelta(days=365)
    ]

    analytics.eur_min_30d = _min_for_days(prices, now, 30)
    analytics.eur_min_90d = _min_for_days(prices, now, 90)
    analytics.eur_min_180d = _min_for_days(prices, now, 180)
    analytics.eur_min_365d = _min_for_days(prices, now, 365)
    analytics.eur_min_all_time = min(all_prices) if all_prices else None
    analytics.eur_avg_365d = sum(prices_365d) / len(prices_365d) if prices_365d else None
    analytics.eur_lowest_10pct_365d_threshold = _lowest_10_percent_threshold(prices_365d)
    analytics.calculated_at = now

    await session.flush()
    return analytics


async def get_price_analytics(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    store_id: uuid.UUID | None = None,
) -> PriceAnalytics | None:
    query = select(PriceAnalytics).where(PriceAnalytics.product_id == product_id)
    if store_id is None:
        query = query.where(PriceAnalytics.store_id.is_(None))
    else:
        query = query.where(PriceAnalytics.store_id == store_id)
    return await session.scalar(query)


async def attach_offer_flags(session: AsyncSession, offer: Offer) -> None:
    analytics = await get_price_analytics(
        session,
        product_id=offer.product_id,
        store_id=offer.store_id,
    )
    eur_price = float(offer.eur_price)
    offer.is_historical_min = bool(
        analytics
        and analytics.eur_min_all_time is not None
        and eur_price <= analytics.eur_min_all_time
    )
    offer.is_lowest_10_percent_365d = bool(
        analytics
        and analytics.eur_lowest_10pct_365d_threshold is not None
        and eur_price <= analytics.eur_lowest_10pct_365d_threshold
    )


def _min_for_days(
    prices: list[tuple[float, datetime]],
    now: datetime,
    days: int,
) -> float | None:
    cutoff = now - timedelta(days=days)
    values = [price for price, captured_at in prices if captured_at >= cutoff]
    return min(values) if values else None


def _lowest_10_percent_threshold(prices: list[float]) -> float | None:
    if not prices:
        return None
    sorted_prices = sorted(prices)
    index = max(ceil(len(sorted_prices) * 0.1) - 1, 0)
    return sorted_prices[index]


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
