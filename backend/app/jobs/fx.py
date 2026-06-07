from app.core.celery_app import celery_app
from app.core.config import settings
from app.domains.fx.service import update_fx_rates_from_http_source
from app.jobs.utils import run_async_job


@celery_app.task(name="fx.update_rates")
def update_fx_rates_task() -> dict[str, int]:
    async def handler(session):
        stats = await update_fx_rates_from_http_source(
            session,
            source_url=settings.fx_rate_source_url,
            currencies=settings.fx_currencies,
        )
        await session.commit()
        return {"updated": stats.updated, "skipped": stats.skipped}

    return run_async_job(handler)
