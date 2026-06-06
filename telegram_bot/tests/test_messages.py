from bot.backend_client import ShoppingRequestResult
from bot.config import BotSettings
from bot.messages import (
    help_reply,
    shopping_request_created_reply,
    shopping_request_failed_reply,
    shopping_text_reply,
    start_reply,
)


def test_start_reply_includes_webapp_url() -> None:
    settings = BotSettings(
        telegram_bot_token="token",
        telegram_webapp_url="https://kupikupi.example/app",
    )

    reply = start_reply(settings)

    assert "Kupikupi" in reply.text
    assert reply.webapp_url == "https://kupikupi.example/app"


def test_help_reply_lists_commands() -> None:
    reply = help_reply(BotSettings(telegram_bot_token="token"))

    assert "/start" in reply.text
    assert "/help" in reply.text


def test_shopping_text_reply_trims_and_previews_request() -> None:
    reply = shopping_text_reply(
        BotSettings(telegram_bot_token="token"),
        "  Хочу   беговые кроссовки. Размер 41.  ",
    )

    assert "Хочу беговые кроссовки. Размер 41." in reply.text
    assert "подтвердить" in reply.text


def test_shopping_request_created_reply_summarizes_constraints() -> None:
    reply = shopping_request_created_reply(
        BotSettings(telegram_bot_token="token"),
        ShoppingRequestResult(
            id="request-1",
            status="parsed",
            category="running-shoes",
            size_value="41",
            budget_amount=150,
            display_currency="EUR",
        ),
    )

    assert "Запрос создан" in reply.text
    assert "running-shoes" in reply.text
    assert "41" in reply.text
    assert "150 EUR" in reply.text


def test_shopping_request_failed_reply_points_to_webapp() -> None:
    reply = shopping_request_failed_reply(
        BotSettings(
            telegram_bot_token="token",
            telegram_webapp_url="https://kupikupi.example/app",
        ),
        "Хочу кроссовки",
    )

    assert "не получилось отправить запрос" in reply.text
    assert reply.webapp_url == "https://kupikupi.example/app"
