import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class SourceConfigCreate(BaseModel):
    source_type: str
    endpoint_url: str | None = None
    active: bool = True
    sync_interval_minutes: int | None = Field(default=None, ge=1)
    next_sync_at: datetime | None = None
    settings: dict[str, object] | None = None


class SourceConfigUpdate(BaseModel):
    endpoint_url: str | None = None
    active: bool | None = None
    sync_interval_minutes: int | None = Field(default=None, ge=1)
    next_sync_at: datetime | None = None
    settings: dict[str, object] | None = None


class SourceConfigRead(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    source_type: str
    endpoint_url: str | None
    active: bool
    sync_interval_minutes: int | None
    last_sync_at: datetime | None
    next_sync_at: datetime | None
    settings: dict[str, object] | None

    model_config = ConfigDict(from_attributes=True)


class SourceConfigList(BaseModel):
    items: list[SourceConfigRead]


class ManualSyncRequest(BaseModel):
    store_id: uuid.UUID | None = None
    source_config_id: uuid.UUID | None = None
    source_type: str = "fake"


class SyncRunRead(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID | None
    source_config_id: uuid.UUID | None
    source_type: str
    status: str
    products_seen: int
    offers_seen: int
    failed_offers: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SyncRunList(BaseModel):
    items: list[SyncRunRead]


class SyncRunItemRead(BaseModel):
    id: uuid.UUID
    sync_run_id: uuid.UUID
    external_id: str | None
    status: str
    product_id: uuid.UUID | None
    offer_id: uuid.UUID | None
    error_message: str | None
    raw_data: dict[str, object] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SyncRunItemList(BaseModel):
    items: list[SyncRunItemRead]


class ProductDuplicateCandidateRead(BaseModel):
    product_id: uuid.UUID
    name: str
    model: str | None
    sku: str | None

    model_config = ConfigDict(from_attributes=True)


class ProductDuplicateCandidateGroupRead(BaseModel):
    category_id: uuid.UUID
    brand_id: uuid.UUID | None
    normalized_identity: str
    products: list[ProductDuplicateCandidateRead]

    model_config = ConfigDict(from_attributes=True)


class ProductDuplicateCandidateList(BaseModel):
    items: list[ProductDuplicateCandidateGroupRead]
