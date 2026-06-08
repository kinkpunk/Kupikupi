import argparse
import asyncio
import json
import uuid
from typing import Any

from app.db.session import async_session_factory
from app.domains.stores.models import SourceSyncRun
from app.domains.stores.service import (
    get_source_config,
    list_due_source_configs,
    mark_source_config_synced,
)
from app.domains.stores.sync import run_source_sync
from app.integrations.stores.registry import adapter_from_source_config


async def run_source_config_command(*, source_config_id: str) -> int:
    try:
        parsed_source_config_id = uuid.UUID(source_config_id)
    except ValueError:
        print("Invalid source config UUID.")
        return 2

    async with async_session_factory() as session:
        source_config = await get_source_config(session, parsed_source_config_id)
        if source_config is None:
            print("Source config not found.")
            return 1
        if not source_config.active:
            print("Source config is inactive.")
            return 1

        sync_run = await run_source_sync(
            session,
            adapter=adapter_from_source_config(source_config),
            store_id=source_config.store_id,
            source_config_id=source_config.id,
        )
        await mark_source_config_synced(session, source_config)
        await session.commit()

    print(json.dumps(_sync_run_summary(sync_run), indent=2, sort_keys=True))
    return 0 if sync_run.status == "succeeded" else 1


async def run_due_source_configs_command(*, limit: int) -> int:
    async with async_session_factory() as session:
        source_configs = await list_due_source_configs(session, limit=limit)
        sync_runs: list[SourceSyncRun] = []
        for source_config in source_configs:
            sync_run = await run_source_sync(
                session,
                adapter=adapter_from_source_config(source_config),
                store_id=source_config.store_id,
                source_config_id=source_config.id,
            )
            await mark_source_config_synced(session, source_config)
            sync_runs.append(sync_run)
        await session.commit()

    report = {
        "scheduled": len(sync_runs),
        "succeeded": sum(1 for sync_run in sync_runs if sync_run.status == "succeeded"),
        "partially_failed": sum(
            1 for sync_run in sync_runs if sync_run.status == "partially_failed"
        ),
        "failed": sum(1 for sync_run in sync_runs if sync_run.status == "failed"),
        "runs": [_sync_run_summary(sync_run) for sync_run in sync_runs],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["partially_failed"] == 0 and report["failed"] == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Kupikupi source syncs.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-config-id", help="Run one source config by UUID.")
    group.add_argument("--due", action="store_true", help="Run due active source configs.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum due source configs to run.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.source_config_id:
        raise SystemExit(
            asyncio.run(run_source_config_command(source_config_id=args.source_config_id))
        )
    raise SystemExit(asyncio.run(run_due_source_configs_command(limit=args.limit)))


def _sync_run_summary(sync_run: SourceSyncRun) -> dict[str, Any]:
    return {
        "id": str(sync_run.id),
        "store_id": str(sync_run.store_id) if sync_run.store_id else None,
        "source_config_id": str(sync_run.source_config_id) if sync_run.source_config_id else None,
        "source_type": sync_run.source_type,
        "status": sync_run.status,
        "products_seen": sync_run.products_seen,
        "offers_seen": sync_run.offers_seen,
        "failed_offers": sync_run.failed_offers,
        "error_message": sync_run.error_message,
    }


if __name__ == "__main__":
    main()
