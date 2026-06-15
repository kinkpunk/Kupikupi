import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.db.session import async_session_factory
from app.domains.stores.feed_config import (
    StoreFeedConfig,
    heureka_xml_feed_template,
    srovname_api_feed_template,
    store_feed_template,
    upsert_store_feed_config,
)
from app.domains.stores.models import SourceConfig
from app.integrations.stores.registry import adapter_from_source_config


async def dry_run_config_command(*, config_path: Path, limit: int, min_offers: int = 1) -> int:
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

    report = _dry_run_report(payload=payload, records=records, limit=limit, min_offers=min_offers)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if len(records) >= min_offers else 1


def _dry_run_report(
    *,
    payload: StoreFeedConfig,
    records: list[Any],
    limit: int,
    min_offers: int,
) -> dict[str, Any]:
    offers_seen = len(records)
    products_seen = sum(1 for record in records if record.product is not None)
    eur_prices_seen = sum(1 for record in records if record.eur_price is not None)
    offers_with_sizes = sum(1 for record in records if record.sizes)
    warnings = _dry_run_warnings(
        offers_seen=offers_seen,
        min_offers=min_offers,
        products_seen=products_seen,
        eur_prices_seen=eur_prices_seen,
        offers_with_sizes=offers_with_sizes,
    )
    return {
        "store_name": payload.store.name,
        "source_type": payload.source.source_type,
        "endpoint_url": payload.source.endpoint_url,
        "offers_seen": offers_seen,
        "products_seen": products_seen,
        "eur_prices_seen": eur_prices_seen,
        "offers_with_sizes": offers_with_sizes,
        "currencies": _count_by(records, "source_currency"),
        "availability": _count_by(records, "availability"),
        "warnings": warnings,
        "sample": [_offer_sample(record) for record in records[:limit]],
    }


def _dry_run_warnings(
    *,
    offers_seen: int,
    min_offers: int,
    products_seen: int,
    eur_prices_seen: int,
    offers_with_sizes: int,
) -> list[str]:
    warnings: list[str] = []
    if offers_seen < min_offers:
        warnings.append(f"Feed returned {offers_seen} offers, below required minimum {min_offers}.")
    if offers_seen == 0:
        return warnings
    if products_seen < offers_seen:
        warnings.append("Some offers are missing product details and may not be matched.")
    if eur_prices_seen < offers_seen:
        warnings.append(
            "Some offers are missing EUR normalized prices; check FX rates or currency mapping."
        )
    if offers_with_sizes == 0:
        warnings.append("No offers include sizes; size-based requests may not match this feed.")
    return warnings


def _count_by(records: list[Any], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = getattr(record, field_name)
        key = str(value) if value else "unknown"
        counts[key] = counts.get(key, 0) + 1
    return counts


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
        "--min-offers",
        type=int,
        default=1,
        help="Minimum offers required for dry-run success.",
    )
    parser.add_argument(
        "--print-template",
        action="store_true",
        help="Print an example feed config.",
    )
    parser.add_argument(
        "--template-type",
        choices=("http_csv", "heureka_xml", "srovname_api"),
        default="http_csv",
        help="Feed format for --print-template.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.print_template:
        if args.template_type == "heureka_xml":
            template = heureka_xml_feed_template()
        elif args.template_type == "srovname_api":
            template = srovname_api_feed_template()
        else:
            template = store_feed_template()
        print(json.dumps(template, ensure_ascii=False, indent=2, sort_keys=True))
        raise SystemExit(0)
    if args.config is None:
        print("Provide --config or --print-template.")
        raise SystemExit(2)
    if args.dry_run:
        raise SystemExit(
            asyncio.run(
                dry_run_config_command(
                    config_path=args.config,
                    limit=args.limit,
                    min_offers=args.min_offers,
                )
            )
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
