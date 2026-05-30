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

