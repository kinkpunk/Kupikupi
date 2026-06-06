from dataclasses import dataclass

from bot.backend_client import ShoppingRequestResult, ShoppingRequestSummary, WatchlistSummary
from bot.config import BotSettings


@dataclass(frozen=True)
class BotReply:
    text: str
    webapp_url: str | None = None


def start_reply(settings: BotSettings) -> BotReply:
    text = (
        "Привет! Я Kupikupi, персональный агент покупок.\n\n"
        "Напиши, что хочешь купить: например, "
        '"Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро."\n\n'
        "Пока бот в MVP-режиме: я помогу открыть WebApp и подготовить запрос."
    )
    return BotReply(text=text, webapp_url=settings.telegram_webapp_url)


def help_reply(settings: BotSettings) -> BotReply:
    text = (
        "Что я умею:\n"
        "- принять описание покупки обычным текстом;\n"
        "- передать запрос в Kupikupi WebApp;\n"
        "- позже присылать уведомления о хороших предложениях.\n\n"
        "Команды: /start, /help, /requests, /watchlists, "
        "/pause <id>, /resume <id>, /archive <id>."
    )
    return BotReply(text=text, webapp_url=settings.telegram_webapp_url)


def shopping_text_reply(settings: BotSettings, text: str) -> BotReply:
    normalized = " ".join(text.strip().split())
    preview = normalized[:180]
    reply_text = (
        "Понял запрос:\n"
        f"{preview}\n\n"
        "Следующий шаг: открой Kupikupi WebApp, чтобы подтвердить параметры и создать список."
    )
    return BotReply(text=reply_text, webapp_url=settings.telegram_webapp_url)


def shopping_request_created_reply(
    settings: BotSettings,
    result: ShoppingRequestResult,
) -> BotReply:
    parts = ["Запрос создан в Kupikupi.", f"Статус: {result.status}."]
    details = []
    if result.category:
        details.append(f"категория: {result.category}")
    if result.size_value:
        details.append(f"размер: {result.size_value}")
    if result.budget_amount:
        currency = result.display_currency or "EUR"
        details.append(f"бюджет: {result.budget_amount:g} {currency}")
    if details:
        parts.append("Распознал: " + ", ".join(details) + ".")
    parts.append("Открой WebApp, чтобы проверить параметры и подтвердить список.")
    return BotReply(text="\n".join(parts), webapp_url=settings.telegram_webapp_url)


def shopping_request_failed_reply(settings: BotSettings, text: str) -> BotReply:
    fallback = shopping_text_reply(settings, text)
    return BotReply(
        text=(
            f"{fallback.text}\n\n"
            "Сейчас не получилось отправить запрос в backend. "
            "Можно продолжить через WebApp."
        ),
        webapp_url=fallback.webapp_url,
    )


def shopping_requests_reply(
    settings: BotSettings,
    requests: list[ShoppingRequestSummary],
) -> BotReply:
    if not requests:
        return BotReply(
            text="Пока нет сохраненных запросов. Напиши, что хочешь купить.",
            webapp_url=settings.telegram_webapp_url,
        )

    lines = ["Последние запросы:"]
    for index, request in enumerate(requests, start=1):
        details = _shopping_request_details(request)
        lines.append(f"{index}. {request.raw_text[:80]} — {request.status}{details}")
    return BotReply(text="\n".join(lines), webapp_url=settings.telegram_webapp_url)


def watchlists_reply(
    settings: BotSettings,
    watchlists: list[WatchlistSummary],
) -> BotReply:
    if not watchlists:
        return BotReply(
            text="Активных списков пока нет. Создай запрос и подтверди список в WebApp.",
            webapp_url=settings.telegram_webapp_url,
        )

    lines = ["Активные списки:"]
    for index, watchlist in enumerate(watchlists, start=1):
        title = watchlist.model or watchlist.category or watchlist.type
        details = _watchlist_details(watchlist)
        state = "активен" if watchlist.active else "пауза"
        lines.append(f"{index}. {watchlist.id[:8]} — {title} — {state}{details}")
    return BotReply(text="\n".join(lines), webapp_url=settings.telegram_webapp_url)


def watchlist_action_reply(
    settings: BotSettings,
    watchlist: WatchlistSummary,
    action: str,
) -> BotReply:
    title = watchlist.model or watchlist.category or watchlist.type
    action_text = {
        "pause": "поставлен на паузу",
        "resume": "возобновлен",
        "archive": "отправлен в архив",
    }[action]
    return BotReply(
        text=f"Список {watchlist.id[:8]} ({title}) {action_text}.",
        webapp_url=settings.telegram_webapp_url,
    )


def watchlist_action_usage_reply(settings: BotSettings, command: str) -> BotReply:
    return BotReply(
        text=(
            f"Укажи id списка: /{command} <id>.\n"
            "Id можно взять из команды /watchlists, достаточно первых символов."
        ),
        webapp_url=settings.telegram_webapp_url,
    )


def watchlist_not_found_reply(settings: BotSettings, lookup: str) -> BotReply:
    return BotReply(
        text=f"Не нашел список по id {lookup}. Проверь /watchlists и попробуй еще раз.",
        webapp_url=settings.telegram_webapp_url,
    )


def watchlist_ambiguous_reply(settings: BotSettings, lookup: str) -> BotReply:
    return BotReply(
        text=(
            f"По id {lookup} нашлось несколько списков. "
            "Укажи больше символов из id после /watchlists."
        ),
        webapp_url=settings.telegram_webapp_url,
    )


def backend_unavailable_reply(settings: BotSettings) -> BotReply:
    return BotReply(
        text=(
            "Сейчас не получилось получить данные из backend. "
            "Можно продолжить через WebApp."
        ),
        webapp_url=settings.telegram_webapp_url,
    )


def _shopping_request_details(request: ShoppingRequestSummary) -> str:
    details = []
    if request.category:
        details.append(request.category)
    if request.size_value:
        details.append(f"размер {request.size_value}")
    if request.budget_amount:
        details.append(f"{request.budget_amount:g} {request.display_currency or 'EUR'}")
    if not details:
        return ""
    return f" ({', '.join(details)})"


def _watchlist_details(watchlist: WatchlistSummary) -> str:
    details = []
    if watchlist.size_value:
        details.append(f"размер {watchlist.size_value}")
    if watchlist.target_price:
        currency = watchlist.target_price_currency or "EUR"
        details.append(f"цель {watchlist.target_price:g} {currency}")
    if not details:
        return ""
    return f" ({', '.join(details)})"
