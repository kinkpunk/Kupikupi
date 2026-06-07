import argparse
import asyncio
import json
from pathlib import Path

from app.db.session import async_session_factory
from app.domains.privacy.service import count_user_data, delete_user_data, export_user_data


async def export_command(*, telegram_id: int, output: Path | None) -> int:
    async with async_session_factory() as session:
        payload = await export_user_data(session, telegram_id=telegram_id)

    if payload is None:
        print(f"User with Telegram ID {telegram_id} was not found.")
        return 1

    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if output is None:
        print(encoded)
    else:
        output.write_text(encoded + "\n", encoding="utf-8")
        print(f"Exported user data to {output}")
    return 0


async def delete_command(*, telegram_id: int, confirm: bool) -> int:
    async with async_session_factory() as session:
        if confirm:
            stats = await delete_user_data(session, telegram_id=telegram_id)
            if stats is not None:
                await session.commit()
        else:
            stats = await count_user_data(session, telegram_id=telegram_id)

    if stats is None:
        print(f"User with Telegram ID {telegram_id} was not found.")
        return 1

    prefix = "Deleted" if confirm else "Dry run, would delete"
    print(f"{prefix} data for Telegram ID {telegram_id}:")
    print(json.dumps(stats.as_dict(), indent=2, sort_keys=True))
    if not confirm:
        print("Run again with --confirm to delete.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export or delete Kupikupi user data.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export one user's data as JSON.")
    export_parser.add_argument("--telegram-id", type=int, required=True)
    export_parser.add_argument("--output", type=Path)

    delete_parser = subparsers.add_parser("delete", help="Delete one user's data.")
    delete_parser.add_argument("--telegram-id", type=int, required=True)
    delete_parser.add_argument("--confirm", action="store_true")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "export":
        raise SystemExit(
            asyncio.run(export_command(telegram_id=args.telegram_id, output=args.output))
        )
    if args.command == "delete":
        raise SystemExit(
            asyncio.run(delete_command(telegram_id=args.telegram_id, confirm=args.confirm))
        )
    raise SystemExit(2)


if __name__ == "__main__":
    main()
