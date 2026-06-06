from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import settings
from app.domains.catalog.models import Category, Product
from app.domains.offers.models import Offer, PriceAnalytics
from app.domains.stores.models import Store
from app.jobs.notifications import dispatch_notifications_task


def test_celery_registers_core_tasks() -> None:
    assert "notifications.generate" in celery_app.tasks
    assert "notifications.dispatch" in celery_app.tasks
    assert "analytics.recompute_product" in celery_app.tasks
    assert "analytics.recompute_all" in celery_app.tasks
    assert "seed.mvp_data" in celery_app.tasks
    assert "sync.run_fake" in celery_app.tasks
    assert "sync.run_source_config" in celery_app.tasks
    assert "sync.run_due_source_configs" in celery_app.tasks


def test_dispatch_task_skips_when_telegram_token_missing() -> None:
    original_token = settings.telegram_bot_token
    settings.telegram_bot_token = None
    try:
        assert dispatch_notifications_task(limit=7) == {"sent": 0, "failed": 0, "skipped": 7}
    finally:
        settings.telegram_bot_token = original_token


async def test_recompute_all_analytics_task_logic(db_session_factory) -> None:
    async with db_session_factory() as session:
        category = Category(slug="running-shoes", name="Running Shoes")
        store = Store(name="Footshop", country="CZ", url="https://www.footshop.cz")
        session.add_all([category, store])
        await session.flush()
        product = Product(category_id=category.id, name="New Balance Fresh Foam 1080")
        session.add(product)
        await session.flush()
        session.add(
            Offer(
                product_id=product.id,
                store_id=store.id,
                product_url="https://www.footshop.cz/nb-1080",
                source_price=3290,
                source_currency="CZK",
                eur_price=134.29,
                availability="in_stock",
            )
        )
        await session.commit()

    async with db_session_factory() as session:
        result = await _recompute_all_analytics_for_test(session)
        analytics_count = await session.scalar(select(func.count(PriceAnalytics.id)))
        assert result == {"products": 1}
        assert analytics_count == 1


async def _recompute_all_analytics_for_test(session: AsyncSession) -> dict[str, int]:
    from app.domains.offers.models import Offer
    from app.domains.offers.service import compute_price_analytics

    result = await session.execute(select(Offer.product_id).distinct())
    product_ids = list(result.scalars().all())
    for product_id in product_ids:
        await compute_price_analytics(session, product_id=product_id, store_id=None)
    await session.commit()
    return {"products": len(product_ids)}
