import pytest

from scripts import notification_cycle


async def test_notification_cycle_runs_generation_and_dispatch(
    monkeypatch,
    db_session_factory,
) -> None:
    monkeypatch.setattr(notification_cycle, "async_session_factory", db_session_factory)
    monkeypatch.setattr(notification_cycle.settings, "telegram_bot_token", "test-bot-token")

    result = await notification_cycle.run_notification_cycle()

    assert result == {
        "created": 0,
        "generation_skipped": 0,
        "sent": 0,
        "failed": 0,
        "dispatch_skipped": 0,
    }


async def test_notification_cycle_requires_telegram_token(monkeypatch) -> None:
    monkeypatch.setattr(notification_cycle.settings, "telegram_bot_token", None)

    with pytest.raises(
        RuntimeError,
        match="TELEGRAM_BOT_TOKEN is required for notification delivery",
    ):
        await notification_cycle.run_notification_cycle()
