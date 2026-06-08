import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot.commands import setup_bot_commands
from bot.config import BotSettings, get_settings
from bot.router import build_router

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    configuration_issues = settings.validate_runtime_configuration()
    if configuration_issues:
        raise RuntimeError(" ".join(configuration_issues))

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(settings))
    await setup_bot_commands(bot)
    if settings.bot_run_mode.casefold() == "webhook":
        await _run_webhook(bot, dispatcher, settings)
        return
    await _run_polling(bot, dispatcher, settings)


async def _run_polling(bot: Bot, dispatcher: Dispatcher, settings: BotSettings) -> None:
    await dispatcher.start_polling(
        bot,
        polling_timeout=settings.bot_polling_timeout_seconds,
    )


async def _run_webhook(bot: Bot, dispatcher: Dispatcher, settings: BotSettings) -> None:
    await bot.set_webhook(
        settings.telegram_webhook_url or "",
        secret_token=settings.telegram_webhook_secret,
    )
    app = web.Application()
    handler = SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=settings.telegram_webhook_secret,
    )
    handler.register(app, path=settings.telegram_webhook_path)
    setup_application(app, dispatcher, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.webhook_host, port=settings.webhook_port)
    await site.start()
    logger.info(
        "Telegram webhook server started on %s:%s",
        settings.webhook_host,
        settings.webhook_port,
    )
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
