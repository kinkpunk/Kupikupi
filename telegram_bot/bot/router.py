from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.backend_client import BackendClient, BackendClientError
from bot.config import BotSettings
from bot.keyboards import webapp_keyboard
from bot.messages import (
    backend_unavailable_reply,
    help_reply,
    shopping_request_created_reply,
    shopping_request_failed_reply,
    shopping_requests_reply,
    start_reply,
    watchlists_reply,
)


def build_router(settings: BotSettings) -> Router:
    router = Router()
    backend_client = BackendClient(
        base_url=settings.backend_api_url,
        access_token=settings.backend_access_token,
    )

    @router.message(Command("start"))
    async def handle_start(message: Message) -> None:
        reply = start_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("help"))
    async def handle_help(message: Message) -> None:
        reply = help_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("requests"))
    async def handle_requests(message: Message) -> None:
        try:
            requests = await backend_client.list_shopping_requests()
            reply = shopping_requests_reply(settings, requests)
        except BackendClientError:
            reply = backend_unavailable_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("watchlists"))
    async def handle_watchlists(message: Message) -> None:
        try:
            watchlists = await backend_client.list_watchlists()
            reply = watchlists_reply(settings, watchlists)
        except BackendClientError:
            reply = backend_unavailable_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(F.text)
    async def handle_text(message: Message) -> None:
        text = message.text or ""
        try:
            result = await backend_client.create_shopping_request(text)
            reply = shopping_request_created_reply(settings, result)
        except BackendClientError:
            reply = shopping_request_failed_reply(settings, text)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    return router
