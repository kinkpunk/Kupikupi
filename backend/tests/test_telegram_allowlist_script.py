import pytest

from scripts.telegram_allowlist import build_allowlist_value


def test_build_allowlist_value_deduplicates_and_sorts_ids() -> None:
    value = build_allowlist_value(["456", "123, 456", "789\n123"])

    assert value == "123,456,789"


def test_build_allowlist_value_ignores_empty_items() -> None:
    value = build_allowlist_value([" 123, ,\n456 "])

    assert value == "123,456"


def test_build_allowlist_value_rejects_non_numeric_ids() -> None:
    with pytest.raises(ValueError, match="not-a-number"):
        build_allowlist_value(["123,not-a-number"])
