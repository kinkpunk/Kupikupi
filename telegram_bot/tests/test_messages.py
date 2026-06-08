from bot.backend_client import ShoppingRequestResult, ShoppingRequestSummary, WatchlistSummary
from bot.config import BotSettings
from bot.messages import (
    access_denied_reply,
    backend_unavailable_reply,
    help_reply,
    privacy_reply,
    shopping_request_created_reply,
    shopping_request_failed_reply,
    shopping_requests_reply,
    shopping_text_reply,
    start_reply,
    telegram_id_reply,
    watchlist_action_reply,
    watchlist_action_usage_reply,
    watchlist_ambiguous_reply,
    watchlist_not_found_reply,
    watchlists_reply,
)


def test_start_reply_includes_webapp_url() -> None:
    settings = BotSettings(
        telegram_bot_token="token",
        telegram_webapp_url="https://kupikupi.example/app",
        support_contact_url="mailto:support@example.test",
        privacy_policy_url="https://kupikupi.example/privacy",
    )

    reply = start_reply(settings)

    assert "Kupikupi" in reply.text
    assert "support@example.test" in reply.text
    assert "https://kupikupi.example/privacy" in reply.text
    assert reply.webapp_url == "https://kupikupi.example/app"


def test_help_reply_lists_commands() -> None:
    reply = help_reply(BotSettings(telegram_bot_token="token"))

    assert "/start" in reply.text
    assert "/help" in reply.text
    assert "/id" in reply.text
    assert "/privacy" in reply.text
    assert "/requests" in reply.text
    assert "/watchlists" in reply.text
    assert "/pause" in reply.text
    assert "/resume" in reply.text
    assert "/archive" in reply.text


def test_privacy_reply_includes_notice_and_links() -> None:
    reply = privacy_reply(
        BotSettings(
            telegram_bot_token="token",
            telegram_webapp_url="https://kupikupi.example/app",
            support_contact_url="mailto:support@example.test",
            privacy_policy_url="https://kupikupi.example/privacy",
        )
    )

    assert "Telegram-профиль" in reply.text
    assert "Покупки и платежи" in reply.text
    assert "mailto:support@example.test" in reply.text
    assert "https://kupikupi.example/privacy" in reply.text
    assert reply.webapp_url == "https://kupikupi.example/app"


def test_telegram_id_reply_shows_numeric_id() -> None:
    reply = telegram_id_reply(123456789)

    assert "123456789" in reply.text
    assert "закрытый тест" in reply.text
    assert reply.webapp_url is None


def test_telegram_id_reply_handles_missing_user() -> None:
    reply = telegram_id_reply(None)

    assert "Не удалось определить Telegram ID" in reply.text
    assert reply.webapp_url is None


def test_access_denied_reply_mentions_closed_test_and_support() -> None:
    reply = access_denied_reply(
        BotSettings(
            telegram_bot_token="token",
            support_contact_url="mailto:support@example.test",
        )
    )

    assert "закрытого теста" in reply.text
    assert "mailto:support@example.test" in reply.text
    assert reply.webapp_url is None


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


def test_shopping_requests_reply_lists_recent_requests() -> None:
    reply = shopping_requests_reply(
        BotSettings(telegram_bot_token="token"),
        [
            ShoppingRequestSummary(
                id="request-1",
                raw_text="Хочу беговые кроссовки для ежедневных тренировок. Размер 41.",
                status="parsed",
                category="running-shoes",
                size_value="41",
                budget_amount=150,
                display_currency="EUR",
            ),
        ],
    )

    assert "Последние запросы" in reply.text
    assert "Хочу беговые кроссовки" in reply.text
    assert "parsed" in reply.text
    assert "running-shoes" in reply.text
    assert "150 EUR" in reply.text


def test_shopping_requests_reply_handles_empty_list() -> None:
    reply = shopping_requests_reply(
        BotSettings(
            telegram_bot_token="token",
            telegram_webapp_url="https://kupikupi.example/app",
        ),
        [],
    )

    assert "Пока нет сохраненных запросов" in reply.text
    assert reply.webapp_url == "https://kupikupi.example/app"


def test_watchlists_reply_lists_active_watchlists() -> None:
    reply = watchlists_reply(
        BotSettings(telegram_bot_token="token"),
        [
            WatchlistSummary(
                id="watchlist-1",
                type="product_search",
                active=True,
                archived=False,
                model="Nike Pegasus",
                category="running-shoes",
                size_value="41",
                target_price=150,
                target_price_currency="EUR",
            ),
        ],
    )

    assert "Активные списки" in reply.text
    assert "watchlis" in reply.text
    assert "Nike Pegasus" in reply.text
    assert "активен" in reply.text
    assert "размер 41" in reply.text
    assert "цель 150 EUR" in reply.text


def test_watchlists_reply_handles_empty_list() -> None:
    reply = watchlists_reply(
        BotSettings(
            telegram_bot_token="token",
            telegram_webapp_url="https://kupikupi.example/app",
        ),
        [],
    )

    assert "Активных списков пока нет" in reply.text
    assert reply.webapp_url == "https://kupikupi.example/app"


def test_backend_unavailable_reply_points_to_webapp() -> None:
    reply = backend_unavailable_reply(
        BotSettings(
            telegram_bot_token="token",
            telegram_webapp_url="https://kupikupi.example/app",
        )
    )

    assert "не получилось получить данные" in reply.text
    assert reply.webapp_url == "https://kupikupi.example/app"


def test_watchlist_action_reply_summarizes_pause() -> None:
    reply = watchlist_action_reply(
        BotSettings(telegram_bot_token="token"),
        WatchlistSummary(
            id="watchlist-1",
            type="agent_request",
            active=False,
            archived=False,
            model="Nike Pegasus",
            category="running-shoes",
            size_value="41",
            target_price=150,
            target_price_currency="EUR",
        ),
        "pause",
    )

    assert "watchlis" in reply.text
    assert "Nike Pegasus" in reply.text
    assert "поставлен на паузу" in reply.text


def test_watchlist_action_usage_reply_explains_short_id() -> None:
    reply = watchlist_action_usage_reply(BotSettings(telegram_bot_token="token"), "pause")

    assert "/pause <id>" in reply.text
    assert "достаточно первых символов" in reply.text


def test_watchlist_lookup_error_replies_are_specific() -> None:
    settings = BotSettings(telegram_bot_token="token")

    not_found = watchlist_not_found_reply(settings, "abc")
    ambiguous = watchlist_ambiguous_reply(settings, "abc")

    assert "Не нашел список" in not_found.text
    assert "несколько списков" in ambiguous.text
