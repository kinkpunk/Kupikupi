from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.domains.auth.schemas import TokenPair
from app.domains.users.models import User, UserSession


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at < datetime.now(UTC)


async def create_token_pair(session: AsyncSession, user: User) -> TokenPair:
    refresh_token = create_refresh_token()
    refresh_token_hash = hash_token(refresh_token)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.refresh_token_ttl_seconds)

    session.add(
        UserSession(
            user_id=user.id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
        )
    )
    await session.flush()

    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=refresh_token,
        expires_in=settings.access_token_ttl_seconds,
    )


async def rotate_refresh_token(session: AsyncSession, refresh_token: str) -> TokenPair | None:
    token_hash = hash_token(refresh_token)
    result = await session.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.refresh_token_hash == token_hash)
    )
    row = result.one_or_none()
    if row is None:
        return None

    user_session, user = row
    if _is_expired(user_session.expires_at):
        await session.delete(user_session)
        await session.flush()
        return None

    new_refresh_token = create_refresh_token()
    user_session.refresh_token_hash = hash_token(new_refresh_token)
    user_session.expires_at = datetime.now(UTC) + timedelta(
        seconds=settings.refresh_token_ttl_seconds
    )
    await session.flush()

    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_ttl_seconds,
    )
