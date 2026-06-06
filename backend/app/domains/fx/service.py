from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.fx.models import FxRate
from app.domains.fx.schemas import FxRateCreate


class FxRateNotFoundError(ValueError):
    pass


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
