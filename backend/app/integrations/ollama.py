import json

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.config import Settings
from app.domains.shopping_requests.parser import ParsedShoppingRequest

SUPPORTED_CATEGORIES = ["running-shoes", "sneakers", "clothing", "cosmetics", "coffee"]


class OllamaShoppingRequest(BaseModel):
    category: str | None = None
    use_case: str | None = None
    size_value: str | None = None
    size_system: str | None = None
    preferred_brand: str | None = None
    color: str | None = None
    max_price: float | None = None
    max_price_currency: str | None = None

    model_config = ConfigDict(extra="forbid")


async def parse_with_ollama(
    text: str,
    *,
    settings: Settings,
    client: httpx.AsyncClient | None = None,
) -> ParsedShoppingRequest | None:
    if not settings.ollama_enabled:
        return None

    owns_client = client is None
    http_client = client or httpx.AsyncClient(timeout=settings.ollama_timeout_seconds)
    try:
        response = await http_client.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            json={
                "model": settings.ollama_model,
                "system": (
                    "Extract shopping constraints. Use only one of these category slugs: "
                    f"{', '.join(SUPPORTED_CATEGORIES)}. Use null when unknown. "
                    "Use ISO 4217 currency codes and preserve the user's numeric size."
                ),
                "prompt": text,
                "stream": False,
                "format": OllamaShoppingRequest.model_json_schema(),
                "options": {"temperature": 0},
            },
        )
        response.raise_for_status()
        content = response.json().get("response", "")
        parsed = OllamaShoppingRequest.model_validate(json.loads(content))
    except (
        AttributeError,
        httpx.HTTPError,
        json.JSONDecodeError,
        TypeError,
        ValidationError,
        ValueError,
    ):
        return None
    finally:
        if owns_client:
            await http_client.aclose()

    category = parsed.category if parsed.category in SUPPORTED_CATEGORIES else None
    currency = parsed.max_price_currency.upper() if parsed.max_price_currency else None
    return ParsedShoppingRequest(
        category=category,
        use_case=parsed.use_case,
        size_value=parsed.size_value,
        size_system=parsed.size_system,
        preferred_brand=parsed.preferred_brand,
        color=parsed.color,
        max_price=parsed.max_price,
        max_price_currency=currency,
        attributes={"parser": "ollama-v1", "llm_model": settings.ollama_model},
    )
