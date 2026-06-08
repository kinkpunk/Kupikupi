from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.domains.users.models import User
from scripts.user_data_smoke import run_user_data_smoke


async def test_user_data_smoke_requires_confirm_delete(db_session_factory) -> None:
    with pytest.raises(ValueError, match="requires --confirm-delete"):
        await run_user_data_smoke(
            db_session_factory,
            telegram_id=777000,
            confirm_delete=False,
        )


async def test_user_data_smoke_exports_deletes_and_verifies_user(
    db_session_factory,
    tmp_path,
) -> None:
    async with db_session_factory() as session:
        session.add(
            User(
                telegram_id=777000,
                username="privacy-smoke",
                first_name="Privacy",
                last_name="Smoke",
                created_at=datetime(2026, 6, 8, tzinfo=UTC),
                updated_at=datetime(2026, 6, 8, tzinfo=UTC),
            )
        )
        await session.commit()

    export_output = tmp_path / "kupikupi-user-777000.json"

    report = await run_user_data_smoke(
        db_session_factory,
        telegram_id=777000,
        export_output=export_output,
        confirm_delete=True,
    )

    assert report.exported is True
    assert report.dry_run_counts["users"] == 1
    assert report.deleted_counts == report.dry_run_counts
    assert report.deletion_verified is True
    assert report.export_output == str(export_output)
    assert '"telegram_id": 777000' in export_output.read_text(encoding="utf-8")

    async with db_session_factory() as session:
        user = await session.scalar(select(User).where(User.telegram_id == 777000))

    assert user is None


async def test_user_data_smoke_fails_for_missing_user(db_session_factory) -> None:
    with pytest.raises(ValueError, match="was not found"):
        await run_user_data_smoke(
            db_session_factory,
            telegram_id=404,
            confirm_delete=True,
        )
