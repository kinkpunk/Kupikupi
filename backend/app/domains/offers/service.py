import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.offers.models import Offer, OfferAvailability, PriceSnapshot
from app.domains.offers.schemas import OfferCreate, OfferUpdate


async def create_offer(session: AsyncSession, payload: OfferCreate) -> Offer:
    data = payload.model_dump(exclude={"availability_items"})
    offer = Offer(**data)
    offer.availability_items = [
        OfferAvailability(**item.model_dump()) for item in payload.availability_items
    ]
    session.add(offer)
    await session.flush()
    await create_price_snapshot(session, offer)
    return offer


async def update_offer(session: AsyncSession, offer: Offer, payload: OfferUpdate) -> Offer:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(offer, field, value)
    await session.flush()
    await create_price_snapshot(session, offer)
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
    return await session.scalar(
        select(Offer)
        .options(selectinload(Offer.availability_items))
        .where(Offer.id == offer_id)
    )


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
    return offers, total


async def list_product_price_points(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
) -> list[tuple[PriceSnapshot, uuid.UUID]]:
    result = await session.execute(
        select(PriceSnapshot, Offer.store_id)
        .join(Offer, Offer.id == PriceSnapshot.offer_id)
        .where(Offer.product_id == product_id)
        .order_by(PriceSnapshot.captured_at.asc())
    )
    return list(result.all())

