import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StoreCreate(BaseModel):
    name: str
    country: str = "CZ"
    url: str
    active: bool = True
    delivers_to_cz: bool = True


class StoreUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    active: bool | None = None
    delivers_to_cz: bool | None = None


class StoreRead(BaseModel):
    id: uuid.UUID
    name: str
    country: str
    url: str
    active: bool
    delivers_to_cz: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoreList(BaseModel):
    items: list[StoreRead]


class ManualSyncRequest(BaseModel):
    store_id: uuid.UUID | None = None
    source_type: str = "fake"


class SyncRunRead(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID | None
    source_type: str
    status: str
    products_seen: int
    offers_seen: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SyncRunList(BaseModel):
    items: list[SyncRunRead]
