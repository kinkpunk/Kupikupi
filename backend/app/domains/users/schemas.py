import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    id: uuid.UUID
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language: str
    country: str
    currency: str
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    language: str | None = None
    currency: str | None = None

