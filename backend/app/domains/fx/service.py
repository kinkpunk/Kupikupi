from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.fx.models import FxRate
from app.domains.fx.schemas import FxRateCreate


class FxRateNotFoundError(ValueError):
    pass


class FxRateUpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class FxRateUpdateStats:
    updated: int
    skipped: int


async def create_fx_rate(session: AsyncSession, payload: FxRateCreate) -> FxRate:
    fx_rate = FxRate(
        currency=payload.currency.upper(),
        rate_to_eur=payload.rate_to_eur,
        source=payload.source,
        valid_at=payload.valid_at or datetime.now(UTC),
    )
    session.add(fx_rate)
    await session.flush()
    return fx_rate


async def upsert_fx_rate(session: AsyncSession, payload: FxRateCreate) -> FxRate:
    currency = payload.currency.upper()
    valid_at = payload.valid_at or datetime.now(UTC)
    fx_rate = await session.scalar(
        select(FxRate).where(FxRate.currency == currency, FxRate.valid_at == valid_at)
    )
    if fx_rate is None:
        fx_rate = FxRate(
            currency=currency,
            rate_to_eur=payload.rate_to_eur,
            source=payload.source,
            valid_at=valid_at,
        )
        session.add(fx_rate)
    else:
        fx_rate.rate_to_eur = payload.rate_to_eur
        fx_rate.source = payload.source
    await session.flush()
    return fx_rate


async def list_fx_rates(
    session: AsyncSession,
    *,
    currency: str | None = None,
    limit: int = 50,
) -> list[FxRate]:
    query = select(FxRate)
    if currency:
        query = query.where(FxRate.currency == currency.upper())
    result = await session.execute(query.order_by(FxRate.valid_at.desc()).limit(limit))
    return list(result.scalars().all())


async def get_latest_fx_rate(
    session: AsyncSession,
    *,
    currency: str,
    at: datetime | None = None,
) -> FxRate | None:
    normalized_currency = currency.upper()
    if normalized_currency == "EUR":
        return None

    filters = [FxRate.currency == normalized_currency]
    if at is not None:
        filters.append(FxRate.valid_at <= at)

    result = await session.execute(
        select(FxRate).where(*filters).order_by(FxRate.valid_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def convert_to_eur(
    session: AsyncSession,
    *,
    amount: float | None,
    currency: str,
    at: datetime | None = None,
) -> tuple[float | None, float | None]:
    if amount is None:
        return None, None

    normalized_currency = currency.upper()
    if normalized_currency == "EUR":
        return amount, 1.0

    fx_rate = await get_latest_fx_rate(session, currency=normalized_currency, at=at)
    if fx_rate is None:
        raise FxRateNotFoundError(f"FX rate not found for {normalized_currency}.")
    return round(float(amount) * float(fx_rate.rate_to_eur), 2), float(fx_rate.rate_to_eur)


async def update_fx_rates_from_http_source(
    session: AsyncSession,
    *,
    source_url: str,
    currencies: list[str],
    client: httpx.AsyncClient | None = None,
) -> FxRateUpdateStats:
    normalized_currencies = [currency.upper() for currency in currencies if currency]
    if not normalized_currencies:
        return FxRateUpdateStats(updated=0, skipped=0)

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=10)
        close_client = True

    try:
        response = await client.get(source_url)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise FxRateUpdateError(f"Failed to fetch FX rates: {exc}") from exc
    finally:
        if close_client:
            await client.aclose()

    rates = payload.get("rates")
    if not isinstance(rates, dict):
        raise FxRateUpdateError("FX source response must include a rates object.")

    valid_at = _valid_at_from_payload(payload)
    source = _source_name_from_url(source_url)
    updated = 0
    skipped = 0

    for currency in normalized_currencies:
        if currency == "EUR":
            skipped += 1
            continue

        quoted_rate = rates.get(currency)
        if quoted_rate is None:
            skipped += 1
            continue

        rate_to_eur = _rate_to_eur_from_eur_base(quoted_rate)
        await upsert_fx_rate(
            session,
            FxRateCreate(
                currency=currency,
                rate_to_eur=rate_to_eur,
                source=source,
                valid_at=valid_at,
            ),
        )
        updated += 1

    return FxRateUpdateStats(updated=updated, skipped=skipped)


def _valid_at_from_payload(payload: dict[str, object]) -> datetime:
    date_value = payload.get("date")
    if isinstance(date_value, str) and date_value:
        return datetime.fromisoformat(date_value).replace(tzinfo=UTC)
    return datetime.now(UTC)


def _source_name_from_url(source_url: str) -> str:
    hostname = urlparse(source_url).hostname
    return hostname or "http_fx_source"


def _rate_to_eur_from_eur_base(value: object) -> float:
    quoted_rate = float(value)
    if quoted_rate <= 0:
        raise FxRateUpdateError("FX quoted rate must be greater than zero.")
    return round(1 / quoted_rate, 6)
