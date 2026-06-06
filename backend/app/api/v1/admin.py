import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentAdminUserDep, DbSessionDep
from app.domains.stores.schemas import (
    ManualSyncRequest,
    StoreCreate,
    StoreList,
    StoreRead,
    StoreUpdate,
    SyncRunList,
    SyncRunRead,
)
from app.domains.stores.service import (
    create_store,
    get_store,
    list_stores,
    list_sync_runs,
    update_store,
)
from app.domains.stores.sync import run_source_sync
from app.integrations.stores.fake import FakeStoreSourceAdapter

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


@router.get("/sync-runs", response_model=SyncRunList)
async def admin_list_sync_runs(
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> SyncRunList:
    return SyncRunList(items=await list_sync_runs(session))


@router.post("/sync-runs", response_model=SyncRunRead, status_code=status.HTTP_202_ACCEPTED)
async def admin_trigger_sync_run(
    payload: ManualSyncRequest,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> SyncRunRead:
    if payload.source_type != "fake":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only fake source sync is available in this iteration.",
        )

    sync_run = await run_source_sync(
        session,
        adapter=FakeStoreSourceAdapter(),
        store_id=payload.store_id,
    )
    await session.commit()
    await session.refresh(sync_run)
    return sync_run
