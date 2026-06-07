from sqlalchemy import func, select

from app.core.security import create_access_token, decode_access_token
from app.db.demo_user import DEMO_ADMIN_TELEGRAM_ID, DEMO_USER_TELEGRAM_ID, ensure_demo_user
from app.domains.users.models import User


async def test_ensure_demo_user_is_idempotent(db_session_factory) -> None:
    async with db_session_factory() as session:
        first = await ensure_demo_user(session)
        second = await ensure_demo_user(session)
        await session.commit()

        count = await session.scalar(
            select(func.count(User.id)).where(User.telegram_id == DEMO_USER_TELEGRAM_ID)
        )

    assert first.id == second.id
    assert count == 1
    assert first.is_admin is False


async def test_ensure_demo_admin_user_creates_admin(db_session_factory) -> None:
    async with db_session_factory() as session:
        admin = await ensure_demo_user(session, is_admin=True)
        await session.commit()

        count = await session.scalar(
            select(func.count(User.id)).where(User.telegram_id == DEMO_ADMIN_TELEGRAM_ID)
        )

    assert count == 1
    assert admin.is_admin is True


async def test_demo_user_access_token_subject(db_session_factory) -> None:
    async with db_session_factory() as session:
        user = await ensure_demo_user(session)
        await session.commit()
        token = create_access_token(str(user.id))

    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == str(user.id)
