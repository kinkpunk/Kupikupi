import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BrandCreate(BaseModel):
    name: str
    normalized_name: str | None = None


class BrandRead(BaseModel):
    id: uuid.UUID
    name: str
    normalized_name: str

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    slug: str
    name: str
    parent_id: uuid.UUID | None = None


class CategoryRead(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    slug: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    name: str
    category_id: uuid.UUID
    brand_id: uuid.UUID | None = None
    model: str | None = None
    sku: str | None = None
    image_url: str | None = None
    attributes: dict[str, object] | None = None


class ProductRead(BaseModel):
    id: uuid.UUID
    brand_id: uuid.UUID | None
    category_id: uuid.UUID
    model: str | None
    name: str
    sku: str | None
    image_url: str | None
    attributes: dict[str, object] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductList(BaseModel):
    items: list[ProductRead]
    total: int

