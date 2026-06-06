from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentAdminUserDep, CurrentUserDep, DbSessionDep
from app.core.config import settings
from app.domains.notifications.schemas import (
    NotificationDispatchResult,
    NotificationGenerationResult,
    NotificationList,
)
from app.domains.notifications.service import (
    dispatch_created_notifications,
    generate_notifications,
    list_user_notifications,
)
from app.integrations.telegram.client import TelegramBotClient

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


@router.post("/admin/notifications/dispatch", response_model=NotificationDispatchResult)
async def admin_dispatch_notifications(
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
    limit: int = Query(default=100, ge=1, le=500),
) -> NotificationDispatchResult:
    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Telegram bot token is not configured.",
        )

    stats = await dispatch_created_notifications(
        session,
        telegram_client=TelegramBotClient(bot_token=settings.telegram_bot_token),
        limit=limit,
    )
    await session.commit()
    return NotificationDispatchResult(sent=stats.sent, failed=stats.failed, skipped=stats.skipped)
