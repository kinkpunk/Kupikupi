import argparse
import asyncio
import json
from pathlib import Path

from pydantic import ValidationError

from app.db.session import async_session_factory
from app.domains.stores.feed_config import (
    StoreFeedConfig,
    store_feed_template,
    upsert_store_feed_config,
)


async def apply_config_command(*, config_path: Path) -> int:
    try:
        payload = StoreFeedConfig.model_validate_json(config_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        print(f"Failed to load store feed config: {exc}")
        return 1

    async with async_session_factory() as session:
        result = await upsert_store_feed_config(session, payload)
        await session.commit()
        await session.refresh(result.store)
        await session.refresh(result.source_config)

    print(
        json.dumps(
            {
                "store_id": str(result.store.id),
                "source_config_id": str(result.source_config.id),
                "created_store": result.created_store,
                "created_source_config": result.created_source_config,
                "source_type": result.source_config.source_type,
                "endpoint_url": result.source_config.endpoint_url,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configure a Kupikupi store feed.")
    parser.add_argument("--config", type=Path, help="Path to a JSON store feed config.")
    parser.add_argument(
        "--print-template",
        action="store_true",
        help="Print an example http_csv feed config.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.print_template:
        print(json.dumps(store_feed_template(), ensure_ascii=False, indent=2, sort_keys=True))
        raise SystemExit(0)
    if args.config is None:
        print("Provide --config or --print-template.")
        raise SystemExit(2)
    raise SystemExit(asyncio.run(apply_config_command(config_path=args.config)))


if __name__ == "__main__":
    main()
