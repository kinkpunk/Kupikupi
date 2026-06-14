import re
from dataclasses import dataclass, field

CURRENCY_ALIASES = {
    "eur": "EUR",
    "euro": "EUR",
    "евро": "EUR",
    "€": "EUR",
    "czk": "CZK",
    "kč": "CZK",
    "kc": "CZK",
    "крон": "CZK",
    "кроны": "CZK",
}

CATEGORY_KEYWORDS = [
    (
        "running-shoes",
        [
            "беговые кроссовки",
            "running shoes",
            "run shoes",
            "trail running shoes",
            "для бега",
        ],
    ),
    ("sneakers", ["кроссовки", "sneakers"]),
    ("clothing", ["одежда", "clothing", "куртка", "футболка", "штаны"]),
    ("cosmetics", ["косметика", "cosmetics", "крем", "сыворотка"]),
    ("coffee", ["кофе", "coffee"]),
]

USE_CASE_KEYWORDS = [
    ("daily training", ["ежедневных тренировок", "daily training", "каждый день"]),
    ("marathon training", ["марафон", "marathon"]),
    ("trail running", ["trail running", "trail run", "трейл"]),
    ("lifestyle", ["повседнев", "lifestyle"]),
]

BRAND_KEYWORDS = [
    "New Balance",
    "Nike",
    "Adidas",
    "Asics",
    "Hoka",
    "CeraVe",
]


@dataclass(frozen=True)
class ParsedShoppingRequest:
    category: str | None = None
    use_case: str | None = None
    size_value: str | None = None
    size_system: str | None = None
    preferred_brand: str | None = None
    color: str | None = None
    max_price: float | None = None
    max_price_currency: str | None = None
    attributes: dict[str, object] = field(default_factory=dict)


def parse_shopping_request(text: str) -> ParsedShoppingRequest:
    normalized = text.casefold()
    category = _match_keyword(normalized, CATEGORY_KEYWORDS)
    use_case = _match_keyword(normalized, USE_CASE_KEYWORDS)
    size_value = _extract_size(normalized)
    max_price, currency = _extract_budget(normalized)
    brand = _extract_brand(text)

    return ParsedShoppingRequest(
        category=category,
        use_case=use_case,
        size_value=size_value,
        size_system="EU" if size_value else None,
        preferred_brand=brand,
        max_price=max_price,
        max_price_currency=currency,
        attributes={"parser": "deterministic-v1"},
    )


def merge_parsed_requests(
    deterministic: ParsedShoppingRequest,
    llm: ParsedShoppingRequest | None,
) -> ParsedShoppingRequest:
    if llm is None:
        return deterministic

    return ParsedShoppingRequest(
        category=deterministic.category or llm.category,
        use_case=deterministic.use_case or llm.use_case,
        size_value=deterministic.size_value or llm.size_value,
        size_system=deterministic.size_system or llm.size_system,
        preferred_brand=deterministic.preferred_brand or llm.preferred_brand,
        color=deterministic.color or llm.color,
        max_price=deterministic.max_price or llm.max_price,
        max_price_currency=deterministic.max_price_currency or llm.max_price_currency,
        attributes={
            **deterministic.attributes,
            "parser": "hybrid-v1",
            "llm_model": llm.attributes.get("llm_model"),
        },
    )


def _match_keyword(normalized: str, keyword_groups: list[tuple[str, list[str]]]) -> str | None:
    for value, keywords in keyword_groups:
        if any(keyword.casefold() in normalized for keyword in keywords):
            return value
    return None


def _extract_size(normalized: str) -> str | None:
    match = re.search(r"(?:размер|size)\s*[:#-]?\s*(\d{2}(?:[.,]5)?)", normalized)
    if not match:
        return None
    return match.group(1).replace(",", ".")


def _extract_budget(normalized: str) -> tuple[float | None, str | None]:
    match = re.search(
        r"(?:бюджет|до|under|budget)\s*[:#-]?\s*(\d+(?:[.,]\d+)?)\s*([a-z€čк]+)?",
        normalized,
    )
    if not match:
        return None, None

    amount = float(match.group(1).replace(",", "."))
    currency_raw = (match.group(2) or "eur").strip().casefold()
    return amount, CURRENCY_ALIASES.get(currency_raw, currency_raw.upper())


def _extract_brand(text: str) -> str | None:
    normalized = text.casefold()
    for brand in BRAND_KEYWORDS:
        if brand.casefold() in normalized:
            return brand
    return None
