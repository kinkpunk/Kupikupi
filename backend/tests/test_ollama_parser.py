import json

import httpx

from app.core.config import Settings
from app.integrations.ollama import parse_with_ollama


async def test_ollama_parser_returns_validated_constraints() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "qwen2.5:0.5b"
        assert payload["stream"] is False
        assert payload["options"]["temperature"] == 0
        return httpx.Response(
            200,
            json={
                "response": json.dumps(
                    {
                        "category": "clothing",
                        "use_case": "winter hiking",
                        "size_value": "M",
                        "size_system": "INT",
                        "preferred_brand": None,
                        "color": "green",
                        "max_price": 180,
                        "max_price_currency": "eur",
                    }
                )
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    parsed = await parse_with_ollama(
        "Warm green jacket for winter hikes, size M, under 180 EUR",
        settings=Settings(ollama_enabled=True),
        client=client,
    )
    await client.aclose()

    assert parsed is not None
    assert parsed.category == "clothing"
    assert parsed.use_case == "winter hiking"
    assert parsed.size_value == "M"
    assert parsed.max_price_currency == "EUR"
    assert parsed.attributes["parser"] == "ollama-v1"


async def test_ollama_parser_returns_none_on_invalid_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "not-json"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    parsed = await parse_with_ollama(
        "anything",
        settings=Settings(ollama_enabled=True),
        client=client,
    )
    await client.aclose()

    assert parsed is None
