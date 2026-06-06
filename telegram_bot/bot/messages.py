from dataclasses import dataclass

from bot.backend_client import ShoppingRequestResult
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
        "Команды: /start, /help."
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
