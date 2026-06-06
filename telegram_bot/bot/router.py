from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.backend_client import BackendClient, BackendClientError, WatchlistSummary
from bot.config import BotSettings
from bot.keyboards import webapp_keyboard
from bot.messages import (
    BotReply,
    backend_unavailable_reply,
    help_reply,
    shopping_request_created_reply,
    shopping_request_failed_reply,
    shopping_requests_reply,
    start_reply,
    watchlist_action_reply,
    watchlist_action_usage_reply,
    watchlist_ambiguous_reply,
    watchlist_not_found_reply,
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

    @router.message(Command("pause"))
    async def handle_pause(message: Message, command: CommandObject) -> None:
        reply = await _handle_watchlist_action(
            settings=settings,
            backend_client=backend_client,
            command_name="pause",
            lookup=(command.args or "").strip(),
        )
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("resume"))
    async def handle_resume(message: Message, command: CommandObject) -> None:
        reply = await _handle_watchlist_action(
            settings=settings,
            backend_client=backend_client,
            command_name="resume",
            lookup=(command.args or "").strip(),
        )
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("archive"))
    async def handle_archive(message: Message, command: CommandObject) -> None:
        reply = await _handle_watchlist_action(
            settings=settings,
            backend_client=backend_client,
            command_name="archive",
            lookup=(command.args or "").strip(),
        )
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


async def _handle_watchlist_action(
    *,
    settings: BotSettings,
    backend_client: BackendClient,
    command_name: str,
    lookup: str,
) -> BotReply:
    if not lookup:
        return watchlist_action_usage_reply(settings, command_name)

    try:
        watchlist = await _resolve_watchlist(backend_client, lookup)
        if watchlist is None:
            return watchlist_not_found_reply(settings, lookup)

        if command_name == "pause":
            updated = await backend_client.pause_watchlist(watchlist.id)
        elif command_name == "resume":
            updated = await backend_client.resume_watchlist(watchlist.id)
        else:
            updated = await backend_client.archive_watchlist(watchlist.id)
    except AmbiguousWatchlistLookupError:
        return watchlist_ambiguous_reply(settings, lookup)
    except BackendClientError:
        return backend_unavailable_reply(settings)

    return watchlist_action_reply(settings, updated, command_name)


async def _resolve_watchlist(
    backend_client: BackendClient,
    lookup: str,
) -> WatchlistSummary | None:
    normalized = lookup.lower()
    watchlists = await backend_client.list_watchlists(limit=20)
    matches = [item for item in watchlists if item.id.lower().startswith(normalized)]
    if len(matches) > 1:
        raise AmbiguousWatchlistLookupError
    if not matches:
        return None
    return matches[0]


class AmbiguousWatchlistLookupError(RuntimeError):
    pass
