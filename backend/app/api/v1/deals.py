from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, DbSessionDep
from app.domains.deals.schemas import DealList
from app.domains.deals.service import list_deals

router = APIRouter(prefix="/deals")


@router.get("", response_model=DealList)
async def get_deals(
    session: DbSessionDep,
    current_user: CurrentUserDep,
    category: str | None = None,
    personalized: bool = True,
    max_price_eur: float | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> DealList:
    items, total = await list_deals(
        session,
        user_id=current_user.id if current_user else None,
        category=category,
        personalized=personalized,
        max_price_eur=max_price_eur,
        limit=limit,
        offset=offset,
    )
    return DealList(items=items, total=total)
