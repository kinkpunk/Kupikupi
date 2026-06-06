from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.catalog.models import Brand, Category, Product
from app.domains.catalog.service import normalize_name
from app.domains.offers.models import Offer, OfferAvailability
from app.domains.offers.schemas import OfferAvailabilityCreate, OfferCreate, OfferUpdate
from app.domains.offers.service import create_offer, update_offer
from app.domains.stores.models import SourceProductMapping, SourceSyncRun, SourceSyncRunItem
from app.integrations.stores.base import SourceOfferRecord, StoreSourceAdapter


async def run_source_sync(
    session: AsyncSession,
    *,
    adapter: StoreSourceAdapter,
    store_id,
    source_config_id=None,
) -> SourceSyncRun:
    sync_run = SourceSyncRun(
        store_id=store_id,
        source_config_id=source_config_id,
        source_type=adapter.source_type,
        status="running",
    )
    session.add(sync_run)
    await session.flush()

    try:
        records = await adapter.fetch_offers(store_id=store_id)
        product_ids = set()
        failed_offers = 0
        for record in records:
            try:
                offer = await upsert_offer_from_source_record(
                    session,
                    store_id=store_id,
                    source_config_id=source_config_id,
                    record=record,
                )
                product_ids.add(offer.product_id)
                session.add(
                    SourceSyncRunItem(
                        sync_run_id=sync_run.id,
                        external_id=record.external_id,
                        status="succeeded",
                        product_id=offer.product_id,
                        offer_id=offer.id,
                        raw_data=_source_offer_raw_data(record),
                    )
                )
            except Exception as exc:
                failed_offers += 1
                session.add(
                    SourceSyncRunItem(
                        sync_run_id=sync_run.id,
                        external_id=record.external_id,
                        status="failed",
                        error_message=str(exc),
                        raw_data=_source_offer_raw_data(record),
                    )
                )
        sync_run.products_seen = len(product_ids)
        sync_run.offers_seen = len(records) - failed_offers
        sync_run.failed_offers = failed_offers
        if failed_offers == 0:
            sync_run.status = "succeeded"
        elif sync_run.offers_seen == 0:
            sync_run.status = "failed"
        else:
            sync_run.status = "partially_failed"
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
    source_config_id=None,
    record: SourceOfferRecord,
) -> Offer:
    product_id = await resolve_source_product_id(
        session,
        store_id=store_id,
        source_config_id=source_config_id,
        record=record,
    )
    offer = await session.scalar(
        select(Offer)
        .options(selectinload(Offer.availability_items))
        .where(Offer.store_id == store_id, Offer.external_id == record.external_id)
    )
    if offer is None:
        return await create_offer(
            session,
            OfferCreate(
                product_id=product_id,
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

async def resolve_source_product_id(
    session: AsyncSession,
    *,
    store_id,
    source_config_id,
    record: SourceOfferRecord,
):
    if record.product_id is not None:
        return record.product_id

    if record.product is None:
        raise ValueError("Source offer record must include product_id or product data.")
    if source_config_id is None:
        raise ValueError("Product data sync requires source_config_id.")

    mapping = await session.scalar(
        select(SourceProductMapping).where(
            SourceProductMapping.store_id == store_id,
            SourceProductMapping.source_config_id == source_config_id,
            SourceProductMapping.external_product_id == record.product.external_product_id,
        )
    )
    if mapping is not None:
        mapping.raw_data = _source_product_raw_data(record)
        await session.flush()
        return mapping.product_id

    product = None
    if record.product.sku:
        product = await session.scalar(select(Product).where(Product.sku == record.product.sku))
    if product is None:
        brand = await _get_or_create_brand(session, record.product.brand_name)
        category = await _get_or_create_category(
            session,
            slug=record.product.category_slug,
            name=record.product.category_name,
        )
        product = Product(
            brand_id=brand.id if brand else None,
            category_id=category.id,
            model=record.product.model,
            name=record.product.name,
            sku=record.product.sku,
            image_url=record.product.image_url,
            attributes=record.product.attributes,
        )
        session.add(product)
        await session.flush()

    mapping = SourceProductMapping(
        store_id=store_id,
        source_config_id=source_config_id,
        external_product_id=record.product.external_product_id,
        product_id=product.id,
        raw_data=_source_product_raw_data(record),
    )
    session.add(mapping)
    await session.flush()
    return product.id


async def _get_or_create_brand(session: AsyncSession, name: str | None) -> Brand | None:
    if not name:
        return None
    normalized_name = normalize_name(name)
    brand = await session.scalar(select(Brand).where(Brand.normalized_name == normalized_name))
    if brand is not None:
        return brand
    brand = Brand(name=name, normalized_name=normalized_name)
    session.add(brand)
    await session.flush()
    return brand


async def _get_or_create_category(
    session: AsyncSession,
    *,
    slug: str,
    name: str,
) -> Category:
    category = await session.scalar(select(Category).where(Category.slug == slug))
    if category is not None:
        return category
    category = Category(slug=slug, name=name)
    session.add(category)
    await session.flush()
    return category


def _source_product_raw_data(record: SourceOfferRecord) -> dict[str, object] | None:
    if record.product is None:
        return None
    return {
        "external_product_id": record.product.external_product_id,
        "name": record.product.name,
        "category_slug": record.product.category_slug,
        "category_name": record.product.category_name,
        "brand_name": record.product.brand_name,
        "model": record.product.model,
        "sku": record.product.sku,
        "image_url": record.product.image_url,
        "attributes": record.product.attributes,
    }


def _source_offer_raw_data(record: SourceOfferRecord) -> dict[str, object]:
    return {
        "external_id": record.external_id,
        "product_id": str(record.product_id) if record.product_id else None,
        "product_url": record.product_url,
        "source_price": record.source_price,
        "source_old_price": record.source_old_price,
        "source_currency": record.source_currency,
        "eur_price": record.eur_price,
        "eur_old_price": record.eur_old_price,
        "fx_rate_to_eur": record.fx_rate_to_eur,
        "discount_percent": record.discount_percent,
        "availability": record.availability,
        "sizes": record.sizes,
        "product": _source_product_raw_data(record),
    }
