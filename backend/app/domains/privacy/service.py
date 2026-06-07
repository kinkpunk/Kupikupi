from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.models import Notification
from app.domains.shopping_requests.models import (
    Recommendation,
    ShoppingRequest,
    ShoppingRequestConstraints,
)
from app.domains.users.models import User, UserSession
from app.domains.watchlists.models import Watchlist


@dataclass(frozen=True)
class UserDataStats:
    users: int
    sessions: int
    shopping_requests: int
    shopping_request_constraints: int
    recommendations: int
    watchlists: int
    notifications: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


async def export_user_data(session: AsyncSession, *, telegram_id: int) -> dict[str, Any] | None:
    user = await _get_user(session, telegram_id=telegram_id)
    if user is None:
        return None

    sessions = await _scalars(
        session,
        select(UserSession).where(UserSession.user_id == user.id).order_by(UserSession.created_at),
    )
    shopping_requests = await _scalars(
        session,
        select(ShoppingRequest)
        .where(ShoppingRequest.user_id == user.id)
        .order_by(ShoppingRequest.created_at),
    )
    request_ids = [request.id for request in shopping_requests]
    constraints = await _scalars(
        session,
        select(ShoppingRequestConstraints)
        .where(ShoppingRequestConstraints.request_id.in_(request_ids))
        .order_by(ShoppingRequestConstraints.id),
    )
    recommendations = await _scalars(
        session,
        select(Recommendation)
        .where(Recommendation.request_id.in_(request_ids))
        .order_by(Recommendation.created_at),
    )
    watchlists = await _scalars(
        session,
        select(Watchlist).where(Watchlist.user_id == user.id).order_by(Watchlist.created_at),
    )
    notifications = await _scalars(
        session,
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at),
    )

    constraints_by_request_id = {
        constraint.request_id: _constraint_payload(constraint) for constraint in constraints
    }
    recommendations_by_request_id: dict[UUID, list[dict[str, Any]]] = {}
    for recommendation in recommendations:
        recommendations_by_request_id.setdefault(recommendation.request_id, []).append(
            _recommendation_payload(recommendation)
        )

    stats = UserDataStats(
        users=1,
        sessions=len(sessions),
        shopping_requests=len(shopping_requests),
        shopping_request_constraints=len(constraints),
        recommendations=len(recommendations),
        watchlists=len(watchlists),
        notifications=len(notifications),
    )

    return {
        "schema_version": 1,
        "user": _user_payload(user),
        "sessions": [_session_payload(session_record) for session_record in sessions],
        "shopping_requests": [
            _shopping_request_payload(
                request,
                constraints=constraints_by_request_id.get(request.id),
                recommendations=recommendations_by_request_id.get(request.id, []),
            )
            for request in shopping_requests
        ],
        "watchlists": [_watchlist_payload(watchlist) for watchlist in watchlists],
        "notifications": [_notification_payload(notification) for notification in notifications],
        "summary": stats.as_dict(),
    }


async def count_user_data(session: AsyncSession, *, telegram_id: int) -> UserDataStats | None:
    user = await _get_user(session, telegram_id=telegram_id)
    if user is None:
        return None

    request_ids = await _request_ids(session, user_id=user.id)
    return UserDataStats(
        users=1,
        sessions=await _count(
            session,
            select(func.count(UserSession.id)).where(UserSession.user_id == user.id),
        ),
        shopping_requests=await _count(
            session,
            select(func.count(ShoppingRequest.id)).where(ShoppingRequest.user_id == user.id),
        ),
        shopping_request_constraints=await _count(
            session,
            select(func.count(ShoppingRequestConstraints.id)).where(
                ShoppingRequestConstraints.request_id.in_(request_ids)
            ),
        ),
        recommendations=await _count(
            session,
            select(func.count(Recommendation.id)).where(Recommendation.request_id.in_(request_ids)),
        ),
        watchlists=await _count(
            session,
            select(func.count(Watchlist.id)).where(Watchlist.user_id == user.id),
        ),
        notifications=await _count(
            session,
            select(func.count(Notification.id)).where(Notification.user_id == user.id),
        ),
    )


async def delete_user_data(session: AsyncSession, *, telegram_id: int) -> UserDataStats | None:
    user = await _get_user(session, telegram_id=telegram_id)
    if user is None:
        return None

    request_ids = await _request_ids(session, user_id=user.id)
    stats = await count_user_data(session, telegram_id=telegram_id)
    if stats is None:
        return None

    await session.execute(delete(Notification).where(Notification.user_id == user.id))
    await session.execute(delete(Watchlist).where(Watchlist.user_id == user.id))
    if request_ids:
        await session.execute(
            delete(Recommendation).where(Recommendation.request_id.in_(request_ids))
        )
        await session.execute(
            delete(ShoppingRequestConstraints).where(
                ShoppingRequestConstraints.request_id.in_(request_ids)
            )
        )
    await session.execute(delete(ShoppingRequest).where(ShoppingRequest.user_id == user.id))
    await session.execute(delete(UserSession).where(UserSession.user_id == user.id))
    await session.execute(delete(User).where(User.id == user.id))
    return stats


async def _get_user(session: AsyncSession, *, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def _request_ids(session: AsyncSession, *, user_id: UUID) -> list[UUID]:
    result = await session.execute(
        select(ShoppingRequest.id).where(ShoppingRequest.user_id == user_id)
    )
    return list(result.scalars().all())


async def _count(session: AsyncSession, statement) -> int:
    return int((await session.scalar(statement)) or 0)


async def _scalars(session: AsyncSession, statement) -> list[Any]:
    result = await session.execute(statement)
    return list(result.scalars().all())


def _user_payload(user: User) -> dict[str, Any]:
    return {
        "id": _json_value(user.id),
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language": user.language,
        "country": user.country,
        "currency": user.currency,
        "is_admin": user.is_admin,
        "created_at": _json_value(user.created_at),
        "updated_at": _json_value(user.updated_at),
    }


def _session_payload(session_record: UserSession) -> dict[str, Any]:
    return {
        "id": _json_value(session_record.id),
        "expires_at": _json_value(session_record.expires_at),
        "created_at": _json_value(session_record.created_at),
    }


def _shopping_request_payload(
    request: ShoppingRequest,
    *,
    constraints: dict[str, Any] | None,
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": _json_value(request.id),
        "raw_text": request.raw_text,
        "status": request.status,
        "locale": request.locale,
        "display_currency": request.display_currency,
        "budget_amount": _json_value(request.budget_amount),
        "created_at": _json_value(request.created_at),
        "updated_at": _json_value(request.updated_at),
        "constraints": constraints,
        "recommendations": recommendations,
    }


def _constraint_payload(constraint: ShoppingRequestConstraints) -> dict[str, Any]:
    return {
        "category": constraint.category,
        "use_case": constraint.use_case,
        "size_value": constraint.size_value,
        "size_system": constraint.size_system,
        "preferred_brand": constraint.preferred_brand,
        "color": constraint.color,
        "max_price": _json_value(constraint.max_price),
        "max_price_currency": constraint.max_price_currency,
        "attributes": constraint.attributes,
    }


def _recommendation_payload(recommendation: Recommendation) -> dict[str, Any]:
    return {
        "id": _json_value(recommendation.id),
        "product_id": _json_value(recommendation.product_id),
        "best_offer_id": _json_value(recommendation.best_offer_id),
        "score": _json_value(recommendation.score),
        "reason": recommendation.reason,
        "created_at": _json_value(recommendation.created_at),
    }


def _watchlist_payload(watchlist: Watchlist) -> dict[str, Any]:
    return {
        "id": _json_value(watchlist.id),
        "type": watchlist.type,
        "product_id": _json_value(watchlist.product_id),
        "brand_id": _json_value(watchlist.brand_id),
        "category_id": _json_value(watchlist.category_id),
        "source_request_id": _json_value(watchlist.source_request_id),
        "model": watchlist.model,
        "size_value": watchlist.size_value,
        "size_system": watchlist.size_system,
        "color": watchlist.color,
        "target_price": _json_value(watchlist.target_price),
        "target_price_currency": watchlist.target_price_currency,
        "discount_threshold": _json_value(watchlist.discount_threshold),
        "notify_on_historical_min": watchlist.notify_on_historical_min,
        "active": watchlist.active,
        "archived": watchlist.archived,
        "created_at": _json_value(watchlist.created_at),
        "updated_at": _json_value(watchlist.updated_at),
    }


def _notification_payload(notification: Notification) -> dict[str, Any]:
    return {
        "id": _json_value(notification.id),
        "watchlist_id": _json_value(notification.watchlist_id),
        "shopping_request_id": _json_value(notification.shopping_request_id),
        "offer_id": _json_value(notification.offer_id),
        "type": notification.type,
        "status": notification.status,
        "message": notification.message,
        "dedupe_key": notification.dedupe_key,
        "sent_at": _json_value(notification.sent_at),
        "created_at": _json_value(notification.created_at),
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value
