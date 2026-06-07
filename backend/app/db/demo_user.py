from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users.models import User

DEMO_USER_TELEGRAM_ID = 9_000_001
DEMO_ADMIN_TELEGRAM_ID = 9_000_002


async def ensure_demo_user(
    session: AsyncSession,
    *,
    is_admin: bool = False,
) -> User:
    telegram_id = DEMO_ADMIN_TELEGRAM_ID if is_admin else DEMO_USER_TELEGRAM_ID
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username="kupikupi_demo_admin" if is_admin else "kupikupi_demo",
            first_name="Kupikupi",
            last_name="Demo Admin" if is_admin else "Demo",
            language="ru",
            country="CZ",
            currency="EUR",
            is_admin=is_admin,
        )
        session.add(user)
        await session.flush()
        return user

    user.is_admin = is_admin
    user.language = user.language or "ru"
    user.country = user.country or "CZ"
    user.currency = user.currency or "EUR"
    await session.flush()
    return user
