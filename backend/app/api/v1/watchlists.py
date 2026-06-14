import uuid

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import CurrentUserDep, DbSessionDep
from app.domains.watchlists.schemas import (
    WatchlistCreate,
    WatchlistList,
    WatchlistRead,
    WatchlistUpdate,
)
from app.domains.watchlists.service import (
    create_watchlist,
    delete_watchlist,
    get_watchlist,
    list_watchlists,
    update_watchlist,
)

router = APIRouter(prefix="/watchlists")


@router.get("", response_model=WatchlistList)
async def get_my_watchlists(
    session: DbSessionDep,
    current_user: CurrentUserDep,
    active: bool | None = None,
    archived: bool | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> WatchlistList:
    items, total = await list_watchlists(
        session,
        user_id=current_user.id,
        active=active,
        archived=archived,
        limit=limit,
        offset=offset,
    )
    return WatchlistList(items=items, total=total)


@router.post("", response_model=WatchlistRead, status_code=status.HTTP_201_CREATED)
async def create_my_watchlist(
    payload: WatchlistCreate,
    session: DbSessionDep,
    current_user: CurrentUserDep,
) -> WatchlistRead:
    watchlist = await create_watchlist(session, user_id=current_user.id, payload=payload)
    await session.commit()
    created = await get_watchlist(
        session,
        user_id=current_user.id,
        watchlist_id=watchlist.id,
    )
    assert created is not None
    return created


@router.get("/{watchlist_id}", response_model=WatchlistRead)
async def get_my_watchlist(
    watchlist_id: uuid.UUID,
    session: DbSessionDep,
    current_user: CurrentUserDep,
) -> WatchlistRead:
    watchlist = await get_watchlist(session, user_id=current_user.id, watchlist_id=watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found.")
    return watchlist


@router.put("/{watchlist_id}", response_model=WatchlistRead)
async def update_my_watchlist(
    watchlist_id: uuid.UUID,
    payload: WatchlistUpdate,
    session: DbSessionDep,
    current_user: CurrentUserDep,
) -> WatchlistRead:
    watchlist = await get_watchlist(session, user_id=current_user.id, watchlist_id=watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found.")

    updated = await update_watchlist(session, watchlist=watchlist, payload=payload)
    await session.commit()
    reloaded = await get_watchlist(
        session,
        user_id=current_user.id,
        watchlist_id=updated.id,
    )
    assert reloaded is not None
    return reloaded


@router.post("/{watchlist_id}/pause", response_model=WatchlistRead)
async def pause_my_watchlist(
    watchlist_id: uuid.UUID,
    session: DbSessionDep,
    current_user: CurrentUserDep,
) -> WatchlistRead:
    watchlist = await get_watchlist(session, user_id=current_user.id, watchlist_id=watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found.")

    updated = await update_watchlist(
        session,
        watchlist=watchlist,
        payload=WatchlistUpdate(active=False),
    )
    await session.commit()
    reloaded = await get_watchlist(
        session,
        user_id=current_user.id,
        watchlist_id=updated.id,
    )
    assert reloaded is not None
    return reloaded


@router.post("/{watchlist_id}/archive", response_model=WatchlistRead)
async def archive_my_watchlist(
    watchlist_id: uuid.UUID,
    session: DbSessionDep,
    current_user: CurrentUserDep,
) -> WatchlistRead:
    watchlist = await get_watchlist(session, user_id=current_user.id, watchlist_id=watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found.")

    updated = await update_watchlist(
        session,
        watchlist=watchlist,
        payload=WatchlistUpdate(active=False, archived=True),
    )
    await session.commit()
    reloaded = await get_watchlist(
        session,
        user_id=current_user.id,
        watchlist_id=updated.id,
    )
    assert reloaded is not None
    return reloaded


@router.post("/{watchlist_id}/restore", response_model=WatchlistRead)
async def restore_my_watchlist(
    watchlist_id: uuid.UUID,
    session: DbSessionDep,
    current_user: CurrentUserDep,
) -> WatchlistRead:
    watchlist = await get_watchlist(session, user_id=current_user.id, watchlist_id=watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found.")

    updated = await update_watchlist(
        session,
        watchlist=watchlist,
        payload=WatchlistUpdate(active=True, archived=False),
    )
    await session.commit()
    reloaded = await get_watchlist(
        session,
        user_id=current_user.id,
        watchlist_id=updated.id,
    )
    assert reloaded is not None
    return reloaded


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_watchlist(
    watchlist_id: uuid.UUID,
    session: DbSessionDep,
    current_user: CurrentUserDep,
) -> Response:
    watchlist = await get_watchlist(session, user_id=current_user.id, watchlist_id=watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found.")

    await delete_watchlist(session, watchlist)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
