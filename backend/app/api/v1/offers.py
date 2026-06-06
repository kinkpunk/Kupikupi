import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentAdminUserDep, DbSessionDep
from app.domains.offers.schemas import (
    OfferCreate,
    OfferList,
    OfferRead,
    OfferUpdate,
    PriceHistoryResponse,
    PricePoint,
)
from app.domains.offers.service import (
    compute_price_analytics,
    create_offer,
    get_offer,
    get_price_analytics,
    list_product_offers,
    list_product_price_points,
    update_offer,
)

router = APIRouter()


@router.get("/products/{product_id}/offers", response_model=OfferList)
async def get_product_offers(
    product_id: uuid.UUID,
    session: DbSessionDep,
    size: str | None = None,
    in_stock: bool | None = None,
) -> OfferList:
    items, total = await list_product_offers(
        session,
        product_id=product_id,
        in_stock=in_stock,
        size=size,
    )
    return OfferList(items=items, total=total)


@router.get("/price-history/{product_id}", response_model=PriceHistoryResponse)
async def get_price_history(
    product_id: uuid.UUID,
    session: DbSessionDep,
    period: str = Query(default="90d", pattern="^(30d|90d|180d|365d|all)$"),
) -> PriceHistoryResponse:
    points = await list_product_price_points(session, product_id=product_id, period=period)
    analytics = await get_price_analytics(session, product_id=product_id, store_id=None)
    return PriceHistoryResponse(
        product_id=product_id,
        period=period,
        points=[
            PricePoint(
                captured_at=snapshot.captured_at,
                source_price=snapshot.source_price,
                source_old_price=snapshot.source_old_price,
                source_currency=snapshot.source_currency,
                eur_price=snapshot.eur_price,
                eur_old_price=snapshot.eur_old_price,
                fx_rate_to_eur=snapshot.fx_rate_to_eur,
                discount_percent=snapshot.discount_percent,
                availability=snapshot.availability,
                store_id=store_id,
            )
            for snapshot, store_id in points
        ],
        analytics=analytics,
    )


@router.post("/admin/offers", response_model=OfferRead, status_code=status.HTTP_201_CREATED)
async def admin_create_offer(
    payload: OfferCreate,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> OfferRead:
    offer = await create_offer(session, payload)
    await session.commit()
    offer = await get_offer(session, offer.id)
    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Created offer could not be loaded.",
        )
    return offer


@router.patch("/admin/offers/{offer_id}", response_model=OfferRead)
async def admin_update_offer(
    offer_id: uuid.UUID,
    payload: OfferUpdate,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> OfferRead:
    offer = await get_offer(session, offer_id)
    if offer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found.")

    updated = await update_offer(session, offer, payload)
    await session.commit()
    updated = await get_offer(session, updated.id)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Updated offer could not be loaded.",
        )
    return updated


@router.post("/admin/price-analytics/{product_id}/recompute")
async def admin_recompute_price_analytics(
    product_id: uuid.UUID,
    session: DbSessionDep,
    _admin: CurrentAdminUserDep,
) -> dict[str, str]:
    await compute_price_analytics(session, product_id=product_id, store_id=None)
    await session.commit()
    return {"status": "ok"}
