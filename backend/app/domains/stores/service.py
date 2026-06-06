import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.stores.models import SourceConfig, SourceSyncRun, SourceSyncRunItem, Store
from app.domains.stores.schemas import (
    SourceConfigCreate,
    SourceConfigUpdate,
    StoreCreate,
    StoreUpdate,
)


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
