from fastapi import APIRouter, Header, HTTPException, status

from app.api.deps import DbSessionDep
from app.core.config import settings
from app.domains.auth.schemas import (
    AuthResponse,
    RefreshTokenRequest,
    TelegramAuthRequest,
    TelegramBotUserAuthRequest,
    TokenPair,
)
from app.domains.auth.service import create_token_pair, rotate_refresh_token
from app.domains.auth.telegram import TelegramAuthError, validate_telegram_init_data
from app.domains.users.service import upsert_telegram_user

router = APIRouter(prefix="/auth")


@router.post("/telegram", response_model=AuthResponse)
async def authenticate_telegram(
    payload: TelegramAuthRequest,
    session: DbSessionDep,
) -> AuthResponse:
    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Telegram bot token is not configured.",
        )

    try:
        telegram_user = validate_telegram_init_data(
            payload.init_data,
            bot_token=settings.telegram_bot_token,
        )
    except TelegramAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    user = await upsert_telegram_user(
        session,
        telegram_id=telegram_user.telegram_id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
        language=telegram_user.language,
    )
    tokens = await create_token_pair(session, user)
    await session.commit()
    await session.refresh(user)
    return AuthResponse(user=user, tokens=tokens)


@router.post("/telegram-bot-user", response_model=AuthResponse)
async def authenticate_telegram_bot_user(
    payload: TelegramBotUserAuthRequest,
    session: DbSessionDep,
    x_telegram_bot_token: str | None = Header(default=None),
) -> AuthResponse:
    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Telegram bot token is not configured.",
        )
    if x_telegram_bot_token != settings.telegram_bot_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram bot token is invalid.",
        )

    user = await upsert_telegram_user(
        session,
        telegram_id=payload.telegram_id,
        username=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
        language=payload.language,
    )
    tokens = await create_token_pair(session, user)
    await session.commit()
    await session.refresh(user)
    return AuthResponse(user=user, tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    payload: RefreshTokenRequest,
    session: DbSessionDep,
) -> TokenPair:
    tokens = await rotate_refresh_token(session, payload.refresh_token)
    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired.",
        )

    await session.commit()
    return tokens
