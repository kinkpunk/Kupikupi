from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.models import Notification
from app.domains.stores.models import SourceSyncRun, SourceSyncRunItem
from app.domains.users.models import UserSession


@dataclass(frozen=True)
class RetentionCleanupStats:
    expired_sessions: int
    notifications: int
    source_sync_run_items: int
    source_sync_runs: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


async def cleanup_retained_data(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    notification_retention_days: int,
    source_sync_retention_days: int,
) -> RetentionCleanupStats:
    effective_now = now or datetime.now(UTC)
    notification_cutoff = effective_now - timedelta(days=notification_retention_days)
    source_sync_cutoff = effective_now - timedelta(days=source_sync_retention_days)

    expired_sessions = await _delete_count(
        session,
        delete(UserSession).where(UserSession.expires_at <= effective_now),
    )
    notifications = await _delete_count(
        session,
        delete(Notification).where(Notification.created_at < notification_cutoff),
    )

    old_run_ids_result = await session.execute(
        select(SourceSyncRun.id).where(SourceSyncRun.started_at < source_sync_cutoff)
    )
    old_run_ids = list(old_run_ids_result.scalars().all())
    if old_run_ids:
        source_sync_run_items = await _delete_count(
            session,
            delete(SourceSyncRunItem).where(SourceSyncRunItem.sync_run_id.in_(old_run_ids)),
        )
        source_sync_runs = await _delete_count(
            session,
            delete(SourceSyncRun).where(SourceSyncRun.id.in_(old_run_ids)),
        )
    else:
        source_sync_run_items = 0
        source_sync_runs = 0

    return RetentionCleanupStats(
        expired_sessions=expired_sessions,
        notifications=notifications,
        source_sync_run_items=source_sync_run_items,
        source_sync_runs=source_sync_runs,
    )


async def _delete_count(session: AsyncSession, statement) -> int:
    result = await session.execute(statement)
    return int(result.rowcount or 0)
