import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.catalog.models import Product
from app.domains.notifications.models import Notification
from app.domains.offers.models import Offer
from app.domains.offers.service import attach_offer_flags
from app.domains.users.models import User
from app.domains.watchlists.models import Watchlist
from app.integrations.telegram.client import TelegramDeliveryError, TelegramMessageClient


@dataclass(frozen=True)
class NotificationGenerationStats:
    created: int
    skipped: int


@dataclass(frozen=True)
class NotificationDispatchStats:
    sent: int
    failed: int
    skipped: int


async def list_user_notifications(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int,
    offset: int,
) -> tuple[list[Notification], int]:
    total = await session.scalar(
        select(func.count(Notification.id)).where(Notification.user_id == user_id)
    )
    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total or 0


async def dispatch_created_notifications(
    session: AsyncSession,
    *,
    telegram_client: TelegramMessageClient,
    limit: int = 100,
) -> NotificationDispatchStats:
    result = await session.execute(
        select(Notification, User)
        .join(User, User.id == Notification.user_id)
        .where(Notification.status == "created")
        .order_by(Notification.created_at.asc())
        .limit(limit)
    )
    rows = list(result.all())
    sent = 0
    failed = 0
    skipped = 0

    for notification, user in rows:
        if user.telegram_id is None:
            notification.status = "failed"
            failed += 1
            continue

        try:
            await telegram_client.send_message(
                chat_id=user.telegram_id,
                text=notification.message,
            )
        except TelegramDeliveryError:
            notification.status = "failed"
            failed += 1
        else:
            notification.status = "sent"
            notification.sent_at = datetime.now(UTC)
            sent += 1

    await session.flush()
    return NotificationDispatchStats(sent=sent, failed=failed, skipped=skipped)


async def generate_notifications(session: AsyncSession) -> NotificationGenerationStats:
    watchlists = await _list_active_watchlists(session)
    created = 0
    skipped = 0

    for watchlist in watchlists:
        offers = await _list_matching_offers(session, watchlist)
        for offer, _product in offers:
            await attach_offer_flags(session, offer)
            rules = _evaluate_rules(watchlist, offer)
            for notification_type, message in rules:
                was_created = await _create_notification_if_needed(
                    session,
                    watchlist=watchlist,
                    offer=offer,
                    notification_type=notification_type,
                    message=message,
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

    await session.flush()
    return NotificationGenerationStats(created=created, skipped=skipped)


async def _list_active_watchlists(session: AsyncSession) -> list[Watchlist]:
    result = await session.execute(
        select(Watchlist).where(
            Watchlist.active.is_(True),
            Watchlist.archived.is_(False),
        )
    )
    return list(result.scalars().all())


async def _list_matching_offers(
    session: AsyncSession,
    watchlist: Watchlist,
) -> list[tuple[Offer, Product]]:
    query = (
        select(Offer, Product)
        .join(Product, Product.id == Offer.product_id)
        .options(selectinload(Offer.availability_items))
        .where(Offer.availability.in_(["in_stock", "limited"]))
    )
    if watchlist.product_id is not None:
        query = query.where(Offer.product_id == watchlist.product_id)
    if watchlist.category_id is not None:
        query = query.where(Product.category_id == watchlist.category_id)
    if watchlist.brand_id is not None:
        query = query.where(Product.brand_id == watchlist.brand_id)

    return list((await session.execute(query)).all())


def _evaluate_rules(watchlist: Watchlist, offer: Offer) -> list[tuple[str, str]]:
    rules = []
    if watchlist.target_price is not None and offer.eur_price <= watchlist.target_price:
        rules.append(
            (
                "target_price",
                f"Target price reached: EUR {float(offer.eur_price):.2f}",
            )
        )

    if (
        watchlist.discount_threshold is not None
        and offer.discount_percent is not None
        and offer.discount_percent >= watchlist.discount_threshold
    ):
        rules.append(
            (
                "discount",
                f"Discount threshold reached: {float(offer.discount_percent):.0f}%",
            )
        )

    if watchlist.notify_on_historical_min and getattr(offer, "is_historical_min", False):
        rules.append(("historical_min", "Offer reached historical minimum."))

    if getattr(offer, "is_lowest_10_percent_365d", False):
        rules.append(("lowest_10_percent_365d", "Offer is in the lowest 10% of last 365 days."))

    return rules


async def _create_notification_if_needed(
    session: AsyncSession,
    *,
    watchlist: Watchlist,
    offer: Offer,
    notification_type: str,
    message: str,
) -> bool:
    dedupe_key = f"{watchlist.id}:{offer.id}:{notification_type}"
    existing_id = await session.scalar(
        select(Notification.id).where(Notification.dedupe_key == dedupe_key)
    )
    if existing_id is not None:
        return False

    session.add(
        Notification(
            user_id=watchlist.user_id,
            watchlist_id=watchlist.id,
            shopping_request_id=watchlist.source_request_id,
            offer_id=offer.id,
            type=notification_type,
            status="created",
            message=message,
            dedupe_key=dedupe_key,
        )
    )
    return True
