import asyncio
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory


def run_async_job[T](handler: Callable[[AsyncSession], Awaitable[T]]) -> T:
    async def runner() -> T:
        async with async_session_factory() as session:
            return await handler(session)

    return asyncio.run(runner())
