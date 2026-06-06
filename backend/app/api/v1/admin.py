import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentAdminUserDep, DbSessionDep
from app.domains.stores.schemas import (
    ManualSyncRequest,
    SourceConfigCreate,
    SourceConfigList,
    SourceConfigRead,
    SourceConfigUpdate,
    StoreCreate,
    StoreList,
    StoreRead,
    StoreUpdate,
    SyncRunItemList,
    SyncRunList,
    SyncRunRead,
)
from app.domains.stores.service import (
    create_source_config,
    create_store,
    get_source_config,
    get_store,
    get_sync_run,
    list_source_configs,
    list_stores,
    list_sync_run_items,
    list_sync_runs,
    mark_source_config_synced,
    update_source_config,
    update_store,
)
from app.domains.stores.sync import run_source_sync
from app.integrations.stores.base import UnknownSourceTypeError
from app.integrations.stores.fake import FakeStoreSourceAdapter
from app.integrations.stores.registry import adapter_from_source_config

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


@router.get("/stores/{store_id}/source-configs", response_model=SourceConfigList)
async def admin_list_store_source_configs(
    store_id: uuid.UUID,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> SourceConfigList:
    store = await get_store(session, store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")
    return SourceConfigList(items=await list_source_configs(session, store_id=store_id))


@router.post(
    "/stores/{store_id}/source-configs",
    response_model=SourceConfigRead,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_store_source_config(
    store_id: uuid.UUID,
    payload: SourceConfigCreate,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> SourceConfigRead:
    store = await get_store(session, store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")

    source_config = await create_source_config(session, store_id=store_id, payload=payload)
    await session.commit()
    await session.refresh(source_config)
    return source_config


@router.patch("/source-configs/{source_config_id}", response_model=SourceConfigRead)
async def admin_update_source_config(
    source_config_id: uuid.UUID,
    payload: SourceConfigUpdate,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> SourceConfigRead:
    source_config = await get_source_config(session, source_config_id)
    if source_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source config not found.",
        )

    updated = await update_source_config(session, source_config, payload)
    await session.commit()
    await session.refresh(updated)
    return updated


@router.get("/sync-runs", response_model=SyncRunList)
async def admin_list_sync_runs(
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> SyncRunList:
    return SyncRunList(items=await list_sync_runs(session))


@router.get("/sync-runs/{sync_run_id}/items", response_model=SyncRunItemList)
async def admin_list_sync_run_items(
    sync_run_id: uuid.UUID,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> SyncRunItemList:
    sync_run = await get_sync_run(session, sync_run_id)
    if sync_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sync run not found.")
    return SyncRunItemList(items=await list_sync_run_items(session, sync_run_id=sync_run_id))


@router.post("/sync-runs", response_model=SyncRunRead, status_code=status.HTTP_202_ACCEPTED)
async def admin_trigger_sync_run(
    payload: ManualSyncRequest,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> SyncRunRead:
    if payload.source_config_id is not None:
        source_config = await get_source_config(session, payload.source_config_id)
        if source_config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source config not found.",
            )
        if not source_config.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source config is inactive.",
            )
        try:
            adapter = adapter_from_source_config(source_config)
        except UnknownSourceTypeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        sync_run = await run_source_sync(
            session,
            adapter=adapter,
            store_id=source_config.store_id,
            source_config_id=source_config.id,
        )
        await mark_source_config_synced(session, source_config)
        await session.commit()
        await session.refresh(sync_run)
        return sync_run

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
