import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.models import Brand, Category, Product
from app.domains.catalog.schemas import BrandCreate, CategoryCreate, ProductCreate


def normalize_name(value: str) -> str:
    return " ".join(value.casefold().strip().split())


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
