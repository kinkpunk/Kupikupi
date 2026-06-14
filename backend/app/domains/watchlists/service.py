import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.catalog.models import Brand, Category
from app.domains.shopping_requests.models import ShoppingRequest
from app.domains.watchlists.models import Watchlist
from app.domains.watchlists.schemas import WatchlistCreate, WatchlistUpdate


async def create_watchlist(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: WatchlistCreate,
) -> Watchlist:
    watchlist = Watchlist(user_id=user_id, **payload.model_dump())
    session.add(watchlist)
    await session.flush()
    return watchlist


async def create_watchlist_from_shopping_request(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    request: ShoppingRequest,
) -> Watchlist:
    constraints = request.constraints
    category_id = None
    brand_id = None

    if constraints and constraints.category:
        category_id = await session.scalar(
            select(Category.id).where(Category.slug == constraints.category)
        )

    if constraints and constraints.preferred_brand:
        brand_id = await session.scalar(
            select(Brand.id).where(Brand.normalized_name == constraints.preferred_brand.casefold())
        )

    watchlist = Watchlist(
        user_id=user_id,
        type="agent_request",
        category_id=category_id,
        brand_id=brand_id,
        source_request_id=request.id,
        source_request=request,
        size_value=constraints.size_value if constraints else None,
        size_system=constraints.size_system if constraints else None,
        color=constraints.color if constraints else None,
        target_price=constraints.max_price if constraints else request.budget_amount,
        target_price_currency=(
            constraints.max_price_currency if constraints else request.display_currency
        ),
        active=True,
        archived=False,
        notify_on_historical_min=True,
    )
    session.add(watchlist)
    await session.flush()
    return watchlist


async def list_watchlists(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    active: bool | None,
    archived: bool | None,
    limit: int,
    offset: int,
) -> tuple[list[Watchlist], int]:
    filters = [Watchlist.user_id == user_id]
    if active is not None:
        filters.append(Watchlist.active == active)
    if archived is not None:
        filters.append(Watchlist.archived == archived)

    total_result = await session.execute(select(func.count(Watchlist.id)).where(*filters))
    result = await session.execute(
        select(Watchlist)
        .options(
            selectinload(Watchlist.source_request).selectinload(ShoppingRequest.constraints),
        )
        .where(*filters)
        .order_by(Watchlist.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total_result.scalar_one()


async def get_watchlist(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    watchlist_id: uuid.UUID,
) -> Watchlist | None:
    return await session.scalar(
        select(Watchlist)
        .options(
            selectinload(Watchlist.source_request).selectinload(ShoppingRequest.constraints),
        )
        .where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
    )


async def update_watchlist(
    session: AsyncSession,
    *,
    watchlist: Watchlist,
    payload: WatchlistUpdate,
) -> Watchlist:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(watchlist, field, value)
    await session.flush()
    return watchlist


async def delete_watchlist(session: AsyncSession, watchlist: Watchlist) -> None:
    await session.delete(watchlist)
    await session.flush()
