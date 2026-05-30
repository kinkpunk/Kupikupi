import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.stores.models import Store
from app.domains.stores.schemas import StoreCreate, StoreUpdate


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

