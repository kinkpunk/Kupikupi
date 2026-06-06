import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FxRateCreate(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    rate_to_eur: float = Field(gt=0)
    source: str = "manual"
    valid_at: datetime | None = None


class FxRateRead(BaseModel):
    id: uuid.UUID
    currency: str
    rate_to_eur: float
    source: str
    valid_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FxRateList(BaseModel):
    items: list[FxRateRead]
