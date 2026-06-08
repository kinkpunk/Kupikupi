import json
from pathlib import Path

from app.integrations.stores.base import SourceOfferRecord, SourceProductRecord
from scripts import store_feed
from scripts.store_feed import dry_run_config_command


async def test_store_feed_dry_run_fetches_offers_without_database_write(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    config_path = _write_config(tmp_path)

    monkeypatch.setattr(store_feed, "adapter_from_source_config", _fake_adapter_factory)

    exit_code = await dry_run_config_command(config_path=config_path, limit=1)

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["store_name"] == "Example Store"
    assert output["source_type"] == "http_csv"
    assert output["offers_seen"] == 2
    assert len(output["sample"]) == 1
    assert output["sample"][0]["external_id"] == "feed-1"
    assert output["sample"][0]["product_name"] == "New Balance Fresh Foam 1080"


async def test_store_feed_dry_run_reports_invalid_config(tmp_path, capsys) -> None:
    config_path = tmp_path / "invalid-feed.json"
    config_path.write_text('{"store": {"name": ""}}', encoding="utf-8")

    exit_code = await dry_run_config_command(config_path=config_path, limit=3)

    assert exit_code == 1
    assert "Store feed dry run failed:" in capsys.readouterr().out


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "feed.json"
    config_path.write_text(
        json.dumps(
            {
                "store": {
                    "name": "Example Store",
                    "url": "https://www.example.test",
                    "country": "CZ",
                },
                "source": {
                    "source_type": "http_csv",
                    "endpoint_url": "https://feeds.example.test/offers.csv",
                    "settings": {
                        "columns": {
                            "external_id": "id",
                            "product_url": "url",
                            "source_price": "price",
                            "product_name": "name",
                        }
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return config_path


def _fake_adapter_factory(_source_config):
    return FakeStoreSourceAdapter()


class FakeStoreSourceAdapter:
    async def fetch_offers(self):
        return [
            SourceOfferRecord(
                external_id="feed-1",
                product_id=None,
                product_url="https://shop.example.test/item-1",
                source_price=3290,
                source_old_price=None,
                source_currency="CZK",
                eur_price=134.29,
                eur_old_price=None,
                fx_rate_to_eur=0.040817,
                discount_percent=None,
                availability="in_stock",
                sizes=[{"size_value": "41", "size_system": "EU", "in_stock": True}],
                product=SourceProductRecord(
                    external_product_id="nb-1080",
                    name="New Balance Fresh Foam 1080",
                    category_slug="running-shoes",
                    category_name="Running Shoes",
                ),
            ),
            SourceOfferRecord(
                external_id="feed-2",
                product_id=None,
                product_url="https://shop.example.test/item-2",
                source_price=2490,
                source_old_price=None,
                source_currency="CZK",
                eur_price=101.65,
                eur_old_price=None,
                fx_rate_to_eur=0.040817,
                discount_percent=None,
                availability="in_stock",
            ),
        ]
