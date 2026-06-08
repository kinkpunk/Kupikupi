import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentAdminUserDep, DbSessionDep
from app.domains.catalog.schemas import (
    BrandCreate,
    BrandRead,
    CategoryCreate,
    CategoryRead,
    ProductCreate,
    ProductList,
    ProductMergeRequest,
    ProductMergeResult,
    ProductRead,
)
from app.domains.catalog.service import (
    create_brand,
    create_category,
    create_product,
    get_product,
    list_brands,
    list_categories,
    merge_product,
    search_products,
)

router = APIRouter()


@router.get("/categories", response_model=list[CategoryRead])
async def get_categories(session: DbSessionDep) -> list[CategoryRead]:
    return await list_categories(session)


@router.get("/brands", response_model=list[BrandRead])
async def get_brands(session: DbSessionDep) -> list[BrandRead]:
    return await list_brands(session)


@router.get("/products", response_model=ProductList)
async def get_products(
    session: DbSessionDep,
    q: str | None = None,
    category_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProductList:
    items, total = await search_products(
        session,
        q=q,
        category_id=category_id,
        brand_id=brand_id,
        limit=limit,
        offset=offset,
    )
    return ProductList(items=items, total=total)


@router.get("/products/{product_id}", response_model=ProductRead)
async def get_product_detail(product_id: uuid.UUID, session: DbSessionDep) -> ProductRead:
    product = await get_product(session, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


@router.post("/admin/brands", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
async def admin_create_brand(
    payload: BrandCreate,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> BrandRead:
    brand = await create_brand(session, payload)
    await session.commit()
    await session.refresh(brand)
    return brand


@router.post("/admin/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def admin_create_category(
    payload: CategoryCreate,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> CategoryRead:
    category = await create_category(session, payload)
    await session.commit()
    await session.refresh(category)
    return category


@router.post("/admin/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def admin_create_product(
    payload: ProductCreate,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> ProductRead:
    product = await create_product(session, payload)
    await session.commit()
    await session.refresh(product)
    return product


@router.post("/admin/products/{source_product_id}/merge", response_model=ProductMergeResult)
async def admin_merge_product(
    source_product_id: uuid.UUID,
    payload: ProductMergeRequest,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> ProductMergeResult:
    try:
        result = await merge_product(
            session,
            source_product_id=source_product_id,
            target_product_id=payload.target_product_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return result
