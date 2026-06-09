import re
import unicodedata
import uuid

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.models import Brand, Category, Product, ProductVariant
from app.domains.catalog.schemas import (
    BrandCreate,
    CategoryCreate,
    ProductCreate,
    ProductMergeResult,
)
from app.domains.offers.models import Offer, PriceAnalytics
from app.domains.shopping_requests.models import Recommendation
from app.domains.stores.models import SourceProductMapping, SourceSyncRunItem
from app.domains.watchlists.models import Watchlist


def normalize_name(value: str) -> str:
    return " ".join(_strip_diacritics(value).casefold().strip().split())


def normalize_product_identity(value: str) -> str:
    normalized = _PRODUCT_IDENTITY_SEPARATOR_RE.sub(" ", _strip_diacritics(value).casefold())
    return " ".join(normalized.strip().split())


_PRODUCT_IDENTITY_SEPARATOR_RE = re.compile(r"[^0-9a-z]+")


def _strip_diacritics(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )


async def create_brand(session: AsyncSession, payload: BrandCreate) -> Brand:
    brand = Brand(
        name=payload.name,
        normalized_name=payload.normalized_name or normalize_name(payload.name),
    )
    session.add(brand)
    await session.flush()
    return brand


async def create_category(session: AsyncSession, payload: CategoryCreate) -> Category:
    category = Category(slug=payload.slug, name=payload.name, parent_id=payload.parent_id)
    session.add(category)
    await session.flush()
    return category


async def create_product(session: AsyncSession, payload: ProductCreate) -> Product:
    product = Product(**payload.model_dump())
    session.add(product)
    await session.flush()
    return product


async def list_categories(session: AsyncSession) -> list[Category]:
    result = await session.execute(select(Category).order_by(Category.slug))
    return list(result.scalars().all())


async def list_brands(session: AsyncSession) -> list[Brand]:
    result = await session.execute(select(Brand).order_by(Brand.name))
    return list(result.scalars().all())


async def search_products(
    session: AsyncSession,
    *,
    q: str | None = None,
    category_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Product], int]:
    conditions = []
    if category_id:
        conditions.append(Product.category_id == category_id)
    if brand_id:
        conditions.append(Product.brand_id == brand_id)
    if q:
        pattern = f"%{q.casefold()}%"
        conditions.append(
            or_(
                func.lower(Product.name).like(pattern),
                func.lower(Product.model).like(pattern),
                func.lower(Product.sku).like(pattern),
            )
        )

    query = select(Product)
    count_query = select(func.count(Product.id))
    for condition in conditions:
        query = query.where(condition)
        count_query = count_query.where(condition)

    total_result = await session.execute(count_query)
    result = await session.execute(
        query.order_by(Product.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), total_result.scalar_one()


async def get_product(session: AsyncSession, product_id: uuid.UUID) -> Product | None:
    result = await session.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def merge_product(
    session: AsyncSession,
    *,
    source_product_id: uuid.UUID,
    target_product_id: uuid.UUID,
) -> ProductMergeResult:
    if source_product_id == target_product_id:
        raise ValueError("source and target products must be different.")

    source_product = await get_product(session, source_product_id)
    target_product = await get_product(session, target_product_id)
    if source_product is None:
        raise ValueError("source product was not found.")
    if target_product is None:
        raise ValueError("target product was not found.")

    result = ProductMergeResult(
        source_product_id=source_product_id,
        target_product_id=target_product_id,
        offers_moved=await _move_product_refs(session, Offer, source_product_id, target_product_id),
        price_analytics_moved=await _move_product_refs(
            session,
            PriceAnalytics,
            source_product_id,
            target_product_id,
        ),
        recommendations_moved=await _move_product_refs(
            session,
            Recommendation,
            source_product_id,
            target_product_id,
        ),
        watchlists_moved=await _move_product_refs(
            session,
            Watchlist,
            source_product_id,
            target_product_id,
        ),
        source_mappings_moved=await _move_product_refs(
            session,
            SourceProductMapping,
            source_product_id,
            target_product_id,
        ),
        sync_items_moved=await _move_product_refs(
            session,
            SourceSyncRunItem,
            source_product_id,
            target_product_id,
        ),
        variants_moved=await _move_product_refs(
            session,
            ProductVariant,
            source_product_id,
            target_product_id,
        ),
    )
    await session.execute(delete(Product).where(Product.id == source_product_id))
    await session.flush()
    return result


async def _move_product_refs(
    session: AsyncSession,
    model,
    source_product_id: uuid.UUID,
    target_product_id: uuid.UUID,
) -> int:
    result = await session.execute(
        update(model)
        .where(model.product_id == source_product_id)
        .values(product_id=target_product_id)
    )
    return int(result.rowcount or 0)
