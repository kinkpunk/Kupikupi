import argparse
import asyncio

from app.core.security import create_access_token
from app.db.demo_user import ensure_demo_user
from app.db.session import async_session_factory


async def create_demo_token(*, is_admin: bool) -> tuple[str, str]:
    async with async_session_factory() as session:
        user = await ensure_demo_user(session, is_admin=is_admin)
        await session.commit()
        await session.refresh(user)
        token = create_access_token(str(user.id))
        return str(user.id), token


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local Kupikupi demo user token.")
    parser.add_argument("--admin", action="store_true", help="Create an admin demo token.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    user_id, token = asyncio.run(create_demo_token(is_admin=args.admin))
    print(f"User ID: {user_id}")
    print(f"Access token:\n{token}")
    print(f"\nWebApp local env:\nNEXT_PUBLIC_DEMO_ACCESS_TOKEN={token}")


if __name__ == "__main__":
    main()
