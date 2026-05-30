import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentAdminUserDep, DbSessionDep
from app.domains.stores.schemas import StoreCreate, StoreList, StoreRead, StoreUpdate
from app.domains.stores.service import create_store, get_store, list_stores, update_store

router = APIRouter(prefix="/admin")


@router.get("/stores", response_model=StoreList)
async def admin_list_stores(
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> StoreList:
    return StoreList(items=await list_stores(session))


@router.post("/stores", response_model=StoreRead, status_code=status.HTTP_201_CREATED)
async def admin_create_store(
    payload: StoreCreate,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> StoreRead:
    store = await create_store(session, payload)
    await session.commit()
    await session.refresh(store)
    return store


@router.patch("/stores/{store_id}", response_model=StoreRead)
async def admin_update_store(
    store_id: uuid.UUID,
    payload: StoreUpdate,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> StoreRead:
    store = await get_store(session, store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")

    updated = await update_store(session, store, payload)
    await session.commit()
    await session.refresh(updated)
    return updated

