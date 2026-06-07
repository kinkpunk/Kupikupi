from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.domains.notifications.models import Notification
from app.domains.retention.service import cleanup_retained_data
from app.domains.stores.models import SourceSyncRun, SourceSyncRunItem
from app.domains.users.models import User, UserSession


async def test_cleanup_retained_data_removes_only_expired_and_old_operational_records(
    db_session_factory,
) -> None:
    now = datetime(2026, 6, 7, tzinfo=UTC)

    async with db_session_factory() as session:
        user = User(telegram_id=123456, username="tester")
        session.add(user)
        await session.flush()

        expired_session = UserSession(
            user_id=user.id,
            refresh_token_hash="expired-session-hash",
            expires_at=now - timedelta(seconds=1),
        )
        active_session = UserSession(
            user_id=user.id,
            refresh_token_hash="active-session-hash",
            expires_at=now + timedelta(days=7),
        )
        old_notification = Notification(
            user_id=user.id,
            type="deal",
            status="sent",
            message="Old deal",
            dedupe_key="old-notification",
            created_at=now - timedelta(days=181),
        )
        fresh_notification = Notification(
            user_id=user.id,
            type="deal",
            status="sent",
            message="Fresh deal",
            dedupe_key="fresh-notification",
            created_at=now - timedelta(days=30),
        )
        old_sync_run = SourceSyncRun(
            source_type="http_csv",
            status="finished",
            started_at=now - timedelta(days=91),
        )
        fresh_sync_run = SourceSyncRun(
            source_type="http_csv",
            status="finished",
            started_at=now - timedelta(days=7),
        )
        session.add_all(
            [
                expired_session,
                active_session,
                old_notification,
                fresh_notification,
                old_sync_run,
                fresh_sync_run,
            ]
        )
        await session.flush()
        session.add_all(
            [
                SourceSyncRunItem(sync_run_id=old_sync_run.id, external_id="old", status="ok"),
                SourceSyncRunItem(sync_run_id=fresh_sync_run.id, external_id="fresh", status="ok"),
            ]
        )
        await session.commit()

    async with db_session_factory() as session:
        stats = await cleanup_retained_data(
            session,
            now=now,
            notification_retention_days=180,
            source_sync_retention_days=90,
        )
        await session.commit()

    assert stats.as_dict() == {
        "expired_sessions": 1,
        "notifications": 1,
        "source_sync_run_items": 1,
        "source_sync_runs": 1,
    }

    async with db_session_factory() as session:
        assert await session.scalar(select(func.count(UserSession.id))) == 1
        assert await session.scalar(select(func.count(Notification.id))) == 1
        assert await session.scalar(select(func.count(SourceSyncRun.id))) == 1
        assert await session.scalar(select(func.count(SourceSyncRunItem.id))) == 1

        remaining_session_hash = await session.scalar(select(UserSession.refresh_token_hash))
        remaining_notification_key = await session.scalar(select(Notification.dedupe_key))
        remaining_sync_item_external_id = await session.scalar(
            select(SourceSyncRunItem.external_id)
        )

    assert remaining_session_hash == "active-session-hash"
    assert remaining_notification_key == "fresh-notification"
    assert remaining_sync_item_external_id == "fresh"
