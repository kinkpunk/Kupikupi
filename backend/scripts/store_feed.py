import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.db.session import async_session_factory
from app.domains.stores.feed_config import (
    StoreFeedConfig,
    store_feed_template,
    upsert_store_feed_config,
)
from app.domains.stores.models import SourceConfig
from app.integrations.stores.registry import adapter_from_source_config


async def dry_run_config_command(*, config_path: Path, limit: int) -> int:
    try:
        payload = StoreFeedConfig.model_validate_json(config_path.read_text(encoding="utf-8"))
        source_config = SourceConfig(
            source_type=payload.source.source_type,
            endpoint_url=payload.source.endpoint_url,
            active=payload.source.active,
            sync_interval_minutes=payload.source.sync_interval_minutes,
            settings=payload.source.settings,
        )
        records = await adapter_from_source_config(source_config).fetch_offers()
    except (OSError, ValidationError, ValueError) as exc:
        print(f"Store feed dry run failed: {exc}")
        return 1

    print(
        json.dumps(
            {
                "store_name": payload.store.name,
                "source_type": payload.source.source_type,
                "endpoint_url": payload.source.endpoint_url,
                "offers_seen": len(records),
                "sample": [_offer_sample(record) for record in records[:limit]],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


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
        "--dry-run",
        action="store_true",
        help="Validate the config and fetch offers without writing to the database.",
    )
    parser.add_argument("--limit", type=int, default=3, help="Sample offers to print in dry-run.")
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
    if args.dry_run:
        raise SystemExit(
            asyncio.run(dry_run_config_command(config_path=args.config, limit=args.limit))
        )
    raise SystemExit(asyncio.run(apply_config_command(config_path=args.config)))


def _offer_sample(record) -> dict[str, Any]:
    return {
        "external_id": record.external_id,
        "product_url": record.product_url,
        "source_price": record.source_price,
        "source_currency": record.source_currency,
        "eur_price": record.eur_price,
        "availability": record.availability,
        "product_name": record.product.name if record.product else None,
        "category_slug": record.product.category_slug if record.product else None,
        "sizes": record.sizes,
    }


if __name__ == "__main__":
    main()
