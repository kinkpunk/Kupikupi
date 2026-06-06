from app.core.celery_app import celery_app
from app.core.config import settings
from app.domains.notifications.service import (
    dispatch_created_notifications,
    generate_notifications,
)
from app.integrations.telegram.client import TelegramBotClient
from app.jobs.utils import run_async_job


@celery_app.task(name="notifications.generate")
def generate_notifications_task() -> dict[str, int]:
    async def handler(session):
        stats = await generate_notifications(session)
        await session.commit()
        return {"created": stats.created, "skipped": stats.skipped}

    return run_async_job(handler)


@celery_app.task(name="notifications.dispatch")
def dispatch_notifications_task(limit: int = 100) -> dict[str, int]:
    if not settings.telegram_bot_token:
        return {"sent": 0, "failed": 0, "skipped": limit}

    async def handler(session):
        stats = await dispatch_created_notifications(
            session,
            telegram_client=TelegramBotClient(bot_token=settings.telegram_bot_token),
            limit=limit,
        )
        await session.commit()
        return {"sent": stats.sent, "failed": stats.failed, "skipped": stats.skipped}

    return run_async_job(handler)

