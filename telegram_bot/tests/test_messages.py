from bot.config import BotSettings
from bot.messages import help_reply, shopping_text_reply, start_reply


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
