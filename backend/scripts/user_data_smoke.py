import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import async_session_factory
from app.domains.privacy.service import count_user_data, delete_user_data, export_user_data


@dataclass(frozen=True)
class UserDataSmokeReport:
    telegram_id: int
    exported: bool
    dry_run_counts: dict[str, int]
    deleted_counts: dict[str, int]
    deletion_verified: bool
    export_output: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


async def run_user_data_smoke(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    telegram_id: int,
    export_output: Path | None = None,
    confirm_delete: bool = False,
) -> UserDataSmokeReport:
    if not confirm_delete:
        raise ValueError("user data smoke requires --confirm-delete.")

    async with session_factory() as session:
        payload = await export_user_data(session, telegram_id=telegram_id)
        if payload is None:
            raise ValueError(f"User with Telegram ID {telegram_id} was not found.")

        if export_output is not None:
            export_output.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        dry_run_stats = await count_user_data(session, telegram_id=telegram_id)
        if dry_run_stats is None:
            raise ValueError(f"User with Telegram ID {telegram_id} was not found during dry run.")

        deleted_stats = await delete_user_data(session, telegram_id=telegram_id)
        if deleted_stats is None:
            raise ValueError(f"User with Telegram ID {telegram_id} was not found during delete.")
        await session.commit()

    async with session_factory() as session:
        deletion_verified = await export_user_data(session, telegram_id=telegram_id) is None

    return UserDataSmokeReport(
        telegram_id=telegram_id,
        exported=True,
        dry_run_counts=dry_run_stats.as_dict(),
        deleted_counts=deleted_stats.as_dict(),
        deletion_verified=deletion_verified,
        export_output=str(export_output) if export_output is not None else None,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Kupikupi user data export and deletion on staging restore data."
    )
    parser.add_argument("--telegram-id", type=int, required=True)
    parser.add_argument("--export-output", type=Path)
    parser.add_argument(
        "--confirm-delete",
        action="store_true",
        help="Required because this smoke deletes the selected user from the connected database.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        report = asyncio.run(
            run_user_data_smoke(
                async_session_factory,
                telegram_id=args.telegram_id,
                export_output=args.export_output,
                confirm_delete=args.confirm_delete,
            )
        )
    except ValueError as exc:
        print(f"Kupikupi user data smoke failed: {exc}")
        raise SystemExit(1) from exc

    print("Kupikupi user data smoke passed.")
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    raise SystemExit(0 if report.deletion_verified else 1)


if __name__ == "__main__":
    main()
