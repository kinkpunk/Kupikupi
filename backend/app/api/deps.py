from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import async_session_factory
from app.domains.users.models import User
from app.domains.users.service import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/telegram")
TokenDep = Annotated[str, Depends(oauth2_scheme)]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    token: TokenDep,
    session: DbSessionDep,
) -> User:
    payload = decode_access_token(token)
    subject = payload.get("sub") if payload else None
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
        )

    user = await get_user_by_id(session, subject)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
        )
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_current_admin_user(current_user: CurrentUserDep) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges are required.",
        )
    return current_user


CurrentAdminUserDep = Annotated[User, Depends(get_current_admin_user)]
