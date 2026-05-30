from pydantic import BaseModel

from app.domains.users.schemas import UserRead


class TelegramAuthRequest(BaseModel):
    init_data: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(BaseModel):
    user: UserRead
    tokens: TokenPair

