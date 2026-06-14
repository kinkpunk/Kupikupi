import asyncio
import json

from app.core.config import settings
from app.db.session import async_session_factory
from app.domains.notifications.service import (
    dispatch_created_notifications,
    generate_notifications,
)
from app.integrations.telegram.client import TelegramBotClient


async def run_notification_cycle() -> dict[str, int]:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required for notification delivery.")

    async with async_session_factory() as session:
        generated = await generate_notifications(session)
        dispatched = await dispatch_created_notifications(
            session,
            telegram_client=TelegramBotClient(bot_token=settings.telegram_bot_token),
        )
        await session.commit()

    return {
        "created": generated.created,
        "generation_skipped": generated.skipped,
        "sent": dispatched.sent,
        "failed": dispatched.failed,
        "dispatch_skipped": dispatched.skipped,
    }


def main() -> None:
    print(json.dumps(asyncio.run(run_notification_cycle()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
