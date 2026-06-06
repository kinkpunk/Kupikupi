import uuid

from app.core.celery_app import celery_app
from app.domains.stores.service import (
    get_source_config,
    list_due_source_configs,
    mark_source_config_synced,
)
from app.domains.stores.sync import run_source_sync
from app.integrations.stores.fake import FakeStoreSourceAdapter
from app.integrations.stores.registry import adapter_from_source_config
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


@celery_app.task(name="sync.run_source_config")
def run_source_config_sync_task(source_config_id: str) -> dict[str, str]:
    parsed_source_config_id = uuid.UUID(source_config_id)

    async def handler(session):
        source_config = await get_source_config(session, parsed_source_config_id)
        if source_config is None:
            raise ValueError("Source config not found.")
        if not source_config.active:
            raise ValueError("Source config is inactive.")

        sync_run = await run_source_sync(
            session,
            adapter=adapter_from_source_config(source_config),
            store_id=source_config.store_id,
            source_config_id=source_config.id,
        )
        await mark_source_config_synced(session, source_config)
        await session.commit()
        return {"id": str(sync_run.id), "status": sync_run.status}

    return run_async_job(handler)


@celery_app.task(name="sync.run_due_source_configs")
def run_due_source_configs_task(limit: int = 50) -> dict[str, int]:
    async def handler(session):
        source_configs = await list_due_source_configs(session, limit=limit)
        succeeded = 0
        partially_failed = 0
        failed = 0
        for source_config in source_configs:
            sync_run = await run_source_sync(
                session,
                adapter=adapter_from_source_config(source_config),
                store_id=source_config.store_id,
                source_config_id=source_config.id,
            )
            await mark_source_config_synced(session, source_config)
            if sync_run.status == "succeeded":
                succeeded += 1
            elif sync_run.status == "partially_failed":
                partially_failed += 1
            else:
                failed += 1
        await session.commit()
        return {
            "scheduled": len(source_configs),
            "succeeded": succeeded,
            "partially_failed": partially_failed,
            "failed": failed,
        }

    return run_async_job(handler)
