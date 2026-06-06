import uuid

from app.core.celery_app import celery_app
from app.domains.stores.sync import run_source_sync
from app.integrations.stores.fake import FakeStoreSourceAdapter
from app.jobs.utils import run_async_job


@celery_app.task(name="sync.run_fake")
def run_fake_sync_task(store_id: str | None = None) -> dict[str, str]:
    parsed_store_id = uuid.UUID(store_id) if store_id else None

    async def handler(session):
        sync_run = await run_source_sync(
            session,
            adapter=FakeStoreSourceAdapter(),
            store_id=parsed_store_id,
        )
        await session.commit()
        return {"id": str(sync_run.id), "status": sync_run.status}

    return run_async_job(handler)
