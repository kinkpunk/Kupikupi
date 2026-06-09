import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.catalog.models import Product
from app.domains.catalog.service import normalize_product_identity
from app.domains.stores.models import SourceConfig, SourceSyncRun, SourceSyncRunItem, Store
from app.domains.stores.schemas import (
    SourceConfigCreate,
    SourceConfigUpdate,
    StoreCreate,
    StoreUpdate,
)


@dataclass(frozen=True)
class ProductDuplicateCandidate:
    product_id: uuid.UUID
    name: str
    model: str | None
    sku: str | None


@dataclass(frozen=True)
class ProductDuplicateCandidateGroup:
    category_id: uuid.UUID
    brand_id: uuid.UUID | None
    normalized_identity: str
    products: list[ProductDuplicateCandidate]


async def create_store(session: AsyncSession, payload: StoreCreate) -> Store:
    store = Store(**payload.model_dump())
    session.add(store)
    await session.flush()
    return store


async def list_stores(session: AsyncSession) -> list[Store]:
    result = await session.execute(select(Store).order_by(Store.name))
    return list(result.scalars().all())


async def get_store(session: AsyncSession, store_id: uuid.UUID) -> Store | None:
    result = await session.execute(select(Store).where(Store.id == store_id))
    return result.scalar_one_or_none()


async def update_store(session: AsyncSession, store: Store, payload: StoreUpdate) -> Store:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, field, value)
    await session.flush()
    return store


async def create_source_config(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    payload: SourceConfigCreate,
) -> SourceConfig:
    source_config = SourceConfig(store_id=store_id, **payload.model_dump())
    session.add(source_config)
    await session.flush()
    return source_config


async def get_source_config(
    session: AsyncSession,
    source_config_id: uuid.UUID,
) -> SourceConfig | None:
    result = await session.execute(
        select(SourceConfig).where(SourceConfig.id == source_config_id)
    )
    return result.scalar_one_or_none()


async def list_source_configs(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
) -> list[SourceConfig]:
    result = await session.execute(
        select(SourceConfig)
        .where(SourceConfig.store_id == store_id)
        .order_by(SourceConfig.source_type, SourceConfig.id)
    )
    return list(result.scalars().all())


async def update_source_config(
    session: AsyncSession,
    source_config: SourceConfig,
    payload: SourceConfigUpdate,
) -> SourceConfig:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source_config, field, value)
    await session.flush()
    return source_config


async def list_due_source_configs(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    limit: int = 50,
) -> list[SourceConfig]:
    now = now or datetime.now(UTC)
    result = await session.execute(
        select(SourceConfig)
        .where(
            SourceConfig.active.is_(True),
            SourceConfig.sync_interval_minutes.is_not(None),
            (SourceConfig.next_sync_at.is_(None) | (SourceConfig.next_sync_at <= now)),
        )
        .order_by(SourceConfig.next_sync_at.asc().nullsfirst(), SourceConfig.id.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def mark_source_config_synced(
    session: AsyncSession,
    source_config: SourceConfig,
    *,
    synced_at: datetime | None = None,
) -> SourceConfig:
    synced_at = synced_at or datetime.now(UTC)
    source_config.last_sync_at = synced_at
    if source_config.sync_interval_minutes is None:
        source_config.next_sync_at = None
    else:
        source_config.next_sync_at = synced_at + timedelta(
            minutes=source_config.sync_interval_minutes,
        )
    await session.flush()
    return source_config


async def list_sync_runs(session: AsyncSession) -> list[SourceSyncRun]:
    result = await session.execute(select(SourceSyncRun).order_by(SourceSyncRun.started_at.desc()))
    return list(result.scalars().all())


async def get_sync_run(session: AsyncSession, sync_run_id: uuid.UUID) -> SourceSyncRun | None:
    result = await session.execute(select(SourceSyncRun).where(SourceSyncRun.id == sync_run_id))
    return result.scalar_one_or_none()


async def list_sync_run_items(
    session: AsyncSession,
    *,
    sync_run_id: uuid.UUID,
) -> list[SourceSyncRunItem]:
    result = await session.execute(
        select(SourceSyncRunItem)
        .where(SourceSyncRunItem.sync_run_id == sync_run_id)
        .order_by(SourceSyncRunItem.created_at.asc(), SourceSyncRunItem.id.asc())
    )
    return list(result.scalars().all())


async def list_product_duplicate_candidates(
    session: AsyncSession,
    *,
    limit: int = 50,
) -> list[ProductDuplicateCandidateGroup]:
    result = await session.execute(
        select(Product)
        .options(selectinload(Product.category), selectinload(Product.brand))
        .order_by(Product.category_id, Product.brand_id, Product.name)
    )
    groups: dict[
        tuple[uuid.UUID, uuid.UUID | None, str],
        list[ProductDuplicateCandidate],
    ] = {}
    for product in result.scalars().all():
        identity = _product_duplicate_identity(product)
        if identity is None:
            continue
        key = (product.category_id, product.brand_id, identity)
        groups.setdefault(key, []).append(
            ProductDuplicateCandidate(
                product_id=product.id,
                name=product.name,
                model=product.model,
                sku=product.sku,
            )
        )

    candidates = [
        ProductDuplicateCandidateGroup(
            category_id=category_id,
            brand_id=brand_id,
            normalized_identity=identity,
            products=products,
        )
        for (category_id, brand_id, identity), products in groups.items()
        if len(products) > 1
    ]
    candidates.sort(key=lambda item: (-len(item.products), item.normalized_identity))
    return candidates[:limit]


def _product_duplicate_identity(product: Product) -> str | None:
    value = normalize_product_identity(product.model or product.name)
    if len(value) < 4:
        return None
    return value
