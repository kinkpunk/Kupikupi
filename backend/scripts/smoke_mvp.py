import argparse
import asyncio
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.demo_user import ensure_demo_user
from app.db.seed import seed_mvp_data
from app.db.session import async_session_factory
from app.domains.deals.service import list_deals
from app.domains.notifications.service import generate_notifications
from app.domains.offers.models import Offer
from app.domains.shopping_requests.service import create_shopping_request, list_recommendations
from app.domains.stores.service import list_due_source_configs, mark_source_config_synced
from app.domains.stores.sync import run_source_sync
from app.domains.watchlists.service import create_watchlist_from_shopping_request
from app.integrations.stores.registry import adapter_from_source_config

DEFAULT_REQUEST_TEXT = (
    "Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро."
)


@dataclass(frozen=True)
class SmokeMvpReport:
    user_id: str
    shopping_request_id: str
    watchlist_id: str
    synced_sources: int
    imported_offers: int
    recommendations: int
    deals: int
    notifications_created: int


async def run_mvp_smoke(
    session: AsyncSession,
    *,
    request_text: str = DEFAULT_REQUEST_TEXT,
) -> SmokeMvpReport:
    await seed_mvp_data(session)

    synced_sources = await _sync_due_sources(session)
    user = await ensure_demo_user(session)
    shopping_request = await create_shopping_request(
        session,
        user=user,
        raw_text=request_text,
    )
    recommendations = await list_recommendations(
        session,
        user_id=user.id,
        request_id=shopping_request.id,
    )
    if not recommendations:
        raise RuntimeError("MVP smoke failed: no recommendations were created.")

    imported_offers = await session.scalar(select(func.count(Offer.id)))
    if not imported_offers:
        raise RuntimeError("MVP smoke failed: no demo offers were imported.")

    watchlist = await create_watchlist_from_shopping_request(
        session,
        user_id=user.id,
        request=shopping_request,
    )
    deals, deals_total = await list_deals(session, user_id=user.id)
    if deals_total == 0:
        raise RuntimeError("MVP smoke failed: no personalized deals were found.")

    notification_stats = await generate_notifications(session)
    if notification_stats.created == 0:
        raise RuntimeError("MVP smoke failed: no notifications were generated.")

    await session.commit()
    return SmokeMvpReport(
        user_id=str(user.id),
        shopping_request_id=str(shopping_request.id),
        watchlist_id=str(watchlist.id),
        synced_sources=synced_sources,
        imported_offers=imported_offers,
        recommendations=len(recommendations),
        deals=deals_total,
        notifications_created=notification_stats.created,
    )


async def _sync_due_sources(session: AsyncSession) -> int:
    source_configs = await list_due_source_configs(session)
    for source_config in source_configs:
        await run_source_sync(
            session,
            adapter=adapter_from_source_config(source_config),
            store_id=source_config.store_id,
            source_config_id=source_config.id,
        )
        await mark_source_config_synced(session, source_config)
    return len(source_configs)


async def _main(request_text: str) -> SmokeMvpReport:
    async with async_session_factory() as session:
        return await run_mvp_smoke(session, request_text=request_text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Kupikupi local MVP smoke scenario.")
    parser.add_argument(
        "--text",
        default=DEFAULT_REQUEST_TEXT,
        help="Shopping request text for the smoke scenario.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = asyncio.run(_main(args.text))
    print("Kupikupi MVP smoke passed.")
    print(f"User: {report.user_id}")
    print(f"Shopping request: {report.shopping_request_id}")
    print(f"Watchlist: {report.watchlist_id}")
    print(f"Synced sources: {report.synced_sources}")
    print(f"Imported offers: {report.imported_offers}")
    print(f"Recommendations: {report.recommendations}")
    print(f"Deals: {report.deals}")
    print(f"Notifications created: {report.notifications_created}")


if __name__ == "__main__":
    main()
