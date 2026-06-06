from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.offers.models import Offer, OfferAvailability
from app.domains.offers.schemas import OfferAvailabilityCreate, OfferCreate, OfferUpdate
from app.domains.offers.service import create_offer, update_offer
from app.domains.stores.models import SourceSyncRun
from app.integrations.stores.base import SourceOfferRecord, StoreSourceAdapter


async def run_source_sync(
    session: AsyncSession,
    *,
    adapter: StoreSourceAdapter,
    store_id,
) -> SourceSyncRun:
    sync_run = SourceSyncRun(store_id=store_id, source_type=adapter.source_type, status="running")
    session.add(sync_run)
    await session.flush()

    try:
        records = await adapter.fetch_offers(store_id=store_id)
        for record in records:
            await upsert_offer_from_source_record(session, store_id=store_id, record=record)
        sync_run.products_seen = len({record.product_id for record in records})
        sync_run.offers_seen = len(records)
        sync_run.status = "succeeded"
    except Exception as exc:
        sync_run.status = "failed"
        sync_run.error_message = str(exc)
    finally:
        sync_run.finished_at = datetime.now(UTC)
        await session.flush()

    return sync_run


async def upsert_offer_from_source_record(
    session: AsyncSession,
    *,
    store_id,
    record: SourceOfferRecord,
) -> Offer:
    offer = await session.scalar(
        select(Offer).where(Offer.store_id == store_id, Offer.external_id == record.external_id)
    )
    if offer is None:
        return await create_offer(
            session,
            OfferCreate(
                product_id=record.product_id,
                store_id=store_id,
                external_id=record.external_id,
                product_url=record.product_url,
                source_price=record.source_price,
                source_old_price=record.source_old_price,
                source_currency=record.source_currency,
                eur_price=record.eur_price,
                eur_old_price=record.eur_old_price,
                fx_rate_to_eur=record.fx_rate_to_eur,
                discount_percent=record.discount_percent,
                availability=record.availability,
                availability_items=[
                    _availability_from_mapping(item) for item in record.sizes
                ],
            ),
        )

    offer.availability_items.clear()
    offer.availability_items.extend(
        OfferAvailability(**_availability_from_mapping(item).model_dump())
        for item in record.sizes
    )
    return await update_offer(
        session,
        offer,
        OfferUpdate(
            product_url=record.product_url,
            source_price=record.source_price,
            source_old_price=record.source_old_price,
            source_currency=record.source_currency,
            eur_price=record.eur_price,
            eur_old_price=record.eur_old_price,
            fx_rate_to_eur=record.fx_rate_to_eur,
            discount_percent=record.discount_percent,
            availability=record.availability,
        ),
    )


def _availability_from_mapping(item: dict[str, object]) -> OfferAvailabilityCreate:
    return OfferAvailabilityCreate(
        variant_id=item.get("variant_id"),
        size_value=item.get("size_value"),
        size_system=item.get("size_system"),
        color=item.get("color"),
        in_stock=bool(item.get("in_stock", True)),
        stock_count=item.get("stock_count"),
    )
