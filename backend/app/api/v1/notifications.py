from fastapi import APIRouter, Query

from app.api.deps import CurrentAdminUserDep, CurrentUserDep, DbSessionDep
from app.domains.notifications.schemas import NotificationGenerationResult, NotificationList
from app.domains.notifications.service import generate_notifications, list_user_notifications

router = APIRouter()


@router.get("/notifications", response_model=NotificationList)
async def get_my_notifications(
    session: DbSessionDep,
    current_user: CurrentUserDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> NotificationList:
    items, total = await list_user_notifications(
        session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return NotificationList(items=items, total=total)


@router.post("/admin/notifications/generate", response_model=NotificationGenerationResult)
async def admin_generate_notifications(
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> NotificationGenerationResult:
    stats = await generate_notifications(session)
    await session.commit()
    return NotificationGenerationResult(created=stats.created, skipped=stats.skipped)

