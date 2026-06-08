from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.backend_client import (
    BackendClient,
    BackendClientError,
    TelegramUserIdentity,
    WatchlistSummary,
)
from bot.config import BotSettings
from bot.keyboards import webapp_keyboard
from bot.messages import (
    BotReply,
    access_denied_reply,
    backend_unavailable_reply,
    help_reply,
    privacy_reply,
    shopping_request_created_reply,
    shopping_request_failed_reply,
    shopping_requests_reply,
    start_reply,
    telegram_id_reply,
    watchlist_action_reply,
    watchlist_action_usage_reply,
    watchlist_ambiguous_reply,
    watchlist_not_found_reply,
    watchlists_reply,
)


def build_router(settings: BotSettings) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def handle_start(message: Message) -> None:
        if await _reply_if_access_denied(settings, message):
            return
        reply = start_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("help"))
    async def handle_help(message: Message) -> None:
        if await _reply_if_access_denied(settings, message):
            return
        reply = help_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("id"))
    async def handle_id(message: Message) -> None:
        reply = telegram_id_reply(message.from_user.id if message.from_user else None)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("privacy"))
    async def handle_privacy(message: Message) -> None:
        if await _reply_if_access_denied(settings, message):
            return
        reply = privacy_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("requests"))
    async def handle_requests(message: Message) -> None:
        if await _reply_if_access_denied(settings, message):
            return
        try:
            backend_client = await _backend_client_for_message(settings, message)
            requests = await backend_client.list_shopping_requests()
            reply = shopping_requests_reply(settings, requests)
        except BackendClientError:
            reply = backend_unavailable_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("watchlists"))
    async def handle_watchlists(message: Message) -> None:
        if await _reply_if_access_denied(settings, message):
            return
        try:
            backend_client = await _backend_client_for_message(settings, message)
            watchlists = await backend_client.list_watchlists()
            reply = watchlists_reply(settings, watchlists)
        except BackendClientError:
            reply = backend_unavailable_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("pause"))
    async def handle_pause(message: Message, command: CommandObject) -> None:
        if await _reply_if_access_denied(settings, message):
            return
        try:
            backend_client = await _backend_client_for_message(settings, message)
            reply = await _handle_watchlist_action(
                settings=settings,
                backend_client=backend_client,
                command_name="pause",
                lookup=(command.args or "").strip(),
            )
        except BackendClientError:
            reply = backend_unavailable_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("resume"))
    async def handle_resume(message: Message, command: CommandObject) -> None:
        if await _reply_if_access_denied(settings, message):
            return
        try:
            backend_client = await _backend_client_for_message(settings, message)
            reply = await _handle_watchlist_action(
                settings=settings,
                backend_client=backend_client,
                command_name="resume",
                lookup=(command.args or "").strip(),
            )
        except BackendClientError:
            reply = backend_unavailable_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("archive"))
    async def handle_archive(message: Message, command: CommandObject) -> None:
        if await _reply_if_access_denied(settings, message):
            return
        try:
            backend_client = await _backend_client_for_message(settings, message)
            reply = await _handle_watchlist_action(
                settings=settings,
                backend_client=backend_client,
                command_name="archive",
                lookup=(command.args or "").strip(),
            )
        except BackendClientError:
            reply = backend_unavailable_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(F.text)
    async def handle_text(message: Message) -> None:
        if await _reply_if_access_denied(settings, message):
            return
        text = message.text or ""
        try:
            backend_client = await _backend_client_for_message(settings, message)
            result = await backend_client.create_shopping_request(text)
            reply = shopping_request_created_reply(settings, result)
        except BackendClientError:
            reply = shopping_request_failed_reply(settings, text)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    return router


async def _reply_if_access_denied(settings: BotSettings, message: Message) -> bool:
    allowed_user_ids = settings.allowed_user_ids
    if not allowed_user_ids:
        return False
    if message.from_user is not None and message.from_user.id in allowed_user_ids:
        return False

    reply = access_denied_reply(settings)
    await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))
    return True


async def _backend_client_for_message(settings: BotSettings, message: Message) -> BackendClient:
    if settings.backend_access_token:
        return BackendClient(
            base_url=settings.backend_api_url,
            access_token=settings.backend_access_token,
        )

    if message.from_user is None:
        raise BackendClientError("Telegram message user is missing.")

    auth_client = BackendClient(base_url=settings.backend_api_url, access_token=None)
    access_token = await auth_client.authenticate_telegram_bot_user(
        bot_token=settings.telegram_bot_token,
        user=TelegramUserIdentity(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language=message.from_user.language_code,
        ),
    )
    return BackendClient(base_url=settings.backend_api_url, access_token=access_token)


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
