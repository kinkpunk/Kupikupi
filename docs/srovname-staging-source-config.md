# Srovname Staging Source Config Template

Status date: 2026-06-17

Use this template after Srovname provides a partner API key. Keep the key in the staging secret
group as `SROVNAME_API_KEY`; do not paste it into the JSON config.

## Create The Template

```bash
cd backend
python scripts/store_feed.py --print-template --template-type srovname_api > /tmp/srovname-feed.json
```

Review `/tmp/srovname-feed.json` before dry-run. The generated file should keep this shape:

```json
{
  "store": {
    "name": "Srovname.cz",
    "country": "CZ",
    "url": "https://www.srovname.cz",
    "active": true,
    "delivers_to_cz": true
  },
  "source": {
    "source_type": "srovname_api",
    "endpoint_url": "https://rest.srovname.cz/api/v1/",
    "active": true,
    "sync_interval_minutes": 720,
    "settings": {
      "api_key_env": "SROVNAME_API_KEY",
      "items_per_page": 100,
      "max_pages": 10,
      "default_availability": "in_stock",
      "category_map": {
        "Bezecke boty": {
          "slug": "running-shoes",
          "name": "Running Shoes"
        },
        "Tenisky": {
          "slug": "sneakers",
          "name": "Sneakers"
        }
      }
    }
  }
}
```

## Placeholder Notes

- `store.name`: keep `Srovname.cz` unless the partner account requires a more specific source name.
- `source.endpoint_url`: keep `https://rest.srovname.cz/api/v1/`; the adapter appends
  `eshop/products`.
- `settings.api_key_env`: keep `SROVNAME_API_KEY`; the secret value belongs in Northflank, not in
  this file.
- `settings.items_per_page`: start with `100`; lower it for the first dry-run if Srovname asks for
  conservative test traffic.
- `settings.max_pages`: start with `10`; use a smaller value for first validation if needed.
- `settings.default_availability`: keep `in_stock` until the API response exposes a stronger stock
  field.
- `settings.category_map`: replace or extend the starter Czech category names after the first real
  response. Use Kupikupi category slugs already present in the catalog.

## Validation Flow

```bash
cd backend
python scripts/store_feed.py --config /tmp/srovname-feed.json --dry-run --limit 3 --min-offers 1
python scripts/store_feed.py --config /tmp/srovname-feed.json
python scripts/source_sync.py --due --limit 10
```

Before applying the config, complete `docs/srovname-real-data-intake.md`.
