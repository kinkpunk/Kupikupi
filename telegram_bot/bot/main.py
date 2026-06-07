import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import get_settings
from bot.router import build_router


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    configuration_issues = settings.validate_runtime_configuration()
    if configuration_issues:
        raise RuntimeError(" ".join(configuration_issues))

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(settings))
    await dispatcher.start_polling(
        bot,
        polling_timeout=settings.bot_polling_timeout_seconds,
    )


if __name__ == "__main__":
    asyncio.run(main())
