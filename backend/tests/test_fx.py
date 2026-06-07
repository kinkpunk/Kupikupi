import httpx
from sqlalchemy import select

from app.domains.fx.models import FxRate
from app.domains.fx.service import update_fx_rates_from_http_source


async def test_update_fx_rates_from_http_source_upserts_eur_base_rates(
    db_session_factory,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://fx.example.test/latest?base=EUR&symbols=CZK,PLN"
        return httpx.Response(
            200,
            json={
                "base": "EUR",
                "date": "2026-06-07",
                "rates": {
                    "CZK": 24.5,
                    "PLN": 4.25,
                },
            },
        )

    async with db_session_factory() as session:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            stats = await update_fx_rates_from_http_source(
                session,
                source_url="https://fx.example.test/latest?base=EUR&symbols=CZK,PLN",
                currencies=["CZK", "PLN"],
                client=client,
            )
        await session.commit()

        assert stats.updated == 2
        assert stats.skipped == 0

        rates = list((await session.execute(select(FxRate).order_by(FxRate.currency))).scalars())

    assert [(rate.currency, float(rate.rate_to_eur), rate.source) for rate in rates] == [
        ("CZK", 0.040816, "fx.example.test"),
        ("PLN", 0.235294, "fx.example.test"),
    ]


async def test_update_fx_rates_from_http_source_skips_missing_and_eur(
    db_session_factory,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"date": "2026-06-07", "rates": {"CZK": 25}})

    async with db_session_factory() as session:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            stats = await update_fx_rates_from_http_source(
                session,
                source_url="https://fx.example.test/latest",
                currencies=["CZK", "EUR", "USD"],
                client=client,
            )
        await session.commit()
        count = len(list((await session.execute(select(FxRate))).scalars()))

    assert stats.updated == 1
    assert stats.skipped == 2
    assert count == 1
