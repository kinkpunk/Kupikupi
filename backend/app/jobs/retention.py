from app.core.celery_app import celery_app
from app.core.config import settings
from app.domains.retention.service import cleanup_retained_data
from app.jobs.utils import run_async_job


@celery_app.task(name="retention.cleanup")
def cleanup_retention_task() -> dict[str, int]:
    async def handler(session):
        stats = await cleanup_retained_data(
            session,
            notification_retention_days=settings.notification_retention_days,
            source_sync_retention_days=settings.source_sync_retention_days,
        )
        await session.commit()
        return stats.as_dict()

    return run_async_job(handler)
