import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    watchlist_id: uuid.UUID | None
    shopping_request_id: uuid.UUID | None
    offer_id: uuid.UUID | None
    type: str
    status: str
    message: str
    dedupe_key: str
    sent_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationList(BaseModel):
    items: list[NotificationRead]
    total: int


class NotificationGenerationResult(BaseModel):
    created: int
    skipped: int

