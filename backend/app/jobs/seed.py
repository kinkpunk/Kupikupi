from app.core.celery_app import celery_app
from app.db.seed import seed_mvp_data
from app.jobs.utils import run_async_job


@celery_app.task(name="seed.mvp_data")
def seed_mvp_data_task() -> dict[str, str]:
    async def handler(session):
        await seed_mvp_data(session)
        return {"status": "ok"}

    return run_async_job(handler)
