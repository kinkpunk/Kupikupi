import uuid

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.domains.offers.models import Offer
from app.domains.offers.service import compute_price_analytics
from app.jobs.utils import run_async_job


@celery_app.task(name="analytics.recompute_product")
def recompute_product_analytics_task(product_id: str) -> dict[str, str]:
    parsed_product_id = uuid.UUID(product_id)

    async def handler(session):
        await compute_price_analytics(session, product_id=parsed_product_id, store_id=None)
        await session.commit()
        return {"status": "ok", "product_id": product_id}

    return run_async_job(handler)


@celery_app.task(name="analytics.recompute_all")
def recompute_all_analytics_task() -> dict[str, int]:
    async def handler(session):
        result = await session.execute(select(Offer.product_id).distinct())
        product_ids = list(result.scalars().all())
        for product_id in product_ids:
            await compute_price_analytics(session, product_id=product_id, store_id=None)
        await session.commit()
        return {"products": len(product_ids)}

    return run_async_job(handler)

