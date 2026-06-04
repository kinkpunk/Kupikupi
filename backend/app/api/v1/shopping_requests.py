import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserDep, DbSessionDep
from app.domains.shopping_requests.schemas import (
    RecommendationList,
    ShoppingRequestCreate,
    ShoppingRequestList,
    ShoppingRequestRead,
)
from app.domains.shopping_requests.service import (
    create_shopping_request,
    get_shopping_request,
    list_recommendations,
    list_shopping_requests,
)
from app.domains.watchlists.schemas import WatchlistRead
from app.domains.watchlists.service import create_watchlist_from_shopping_request

router = APIRouter(prefix="/shopping-requests")


@router.get("", response_model=ShoppingRequestList)
async def get_my_shopping_requests(
    session: DbSessionDep,
    current_user: CurrentUserDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ShoppingRequestList:
    items, total = await list_shopping_requests(
        session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return ShoppingRequestList(items=items, total=total)


@router.post("", response_model=ShoppingRequestRead, status_code=status.HTTP_201_CREATED)
async def create_my_shopping_request(
    payload: ShoppingRequestCreate,
    session: DbSessionDep,
    current_user: CurrentUserDep,
) -> ShoppingRequestRead:
    request = await create_shopping_request(session, user=current_user, raw_text=payload.text)
    await session.commit()
    request = await get_shopping_request(session, user_id=current_user.id, request_id=request.id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Created request could not be loaded.",
        )
    return request


@router.get("/{request_id}", response_model=ShoppingRequestRead)
async def get_my_shopping_request(
    request_id: uuid.UUID,
    session: DbSessionDep,
    current_user: CurrentUserDep,
) -> ShoppingRequestRead:
    request = await get_shopping_request(session, user_id=current_user.id, request_id=request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping request not found.",
        )
    return request


@router.get("/{request_id}/recommendations", response_model=RecommendationList)
async def get_my_shopping_request_recommendations(
    request_id: uuid.UUID,
    session: DbSessionDep,
    current_user: CurrentUserDep,
) -> RecommendationList:
    request = await get_shopping_request(session, user_id=current_user.id, request_id=request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping request not found.",
        )

    return RecommendationList(
        items=await list_recommendations(session, user_id=current_user.id, request_id=request_id)
    )


@router.post(
    "/{request_id}/watchlist",
    response_model=WatchlistRead,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_watchlist_from_shopping_request(
    request_id: uuid.UUID,
    session: DbSessionDep,
    current_user: CurrentUserDep,
) -> WatchlistRead:
    request = await get_shopping_request(session, user_id=current_user.id, request_id=request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping request not found.",
        )

    watchlist = await create_watchlist_from_shopping_request(
        session,
        user_id=current_user.id,
        request=request,
    )
    await session.commit()
    await session.refresh(watchlist)
    return watchlist
