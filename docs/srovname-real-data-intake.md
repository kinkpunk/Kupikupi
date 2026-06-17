# Srovname Real Data Intake Checklist

Status date: 2026-06-17

Use this checklist for the first real `srovname_api` dry run before applying the source config on
staging. The goal is to decide whether Srovname data is sufficient for Kupikupi matching,
recommendations, deals, and Telegram notifications.

## Preconditions

- `SROVNAME_API_KEY` is stored in the staging secret group.
- The source config references the key by env name through `settings.api_key_env`.
- The source config does not contain the secret value.
- `category_map` includes the first target categories used in the field test.
- The dry run is limited to a small sample, for example `--limit 3 --min-offers 1`.

## Command

```bash
cd backend
python scripts/store_feed.py --config "$KUPIKUPI_STORE_FEED_CONFIG" --dry-run --limit 3 --min-offers 1
```

## Fields To Record

- Price: `salePrice`, regular price, currency, discount, and EUR-normalized value.
- Product identity: source product ID, product URL, image URL, title, brand, GTIN/EAN, and SKU.
- Category: raw category, Google product category when present, mapped Kupikupi category slug, and
  mapped display name.
- Availability: stock signal, delivery metadata, and whether unavailable products are present.
- Sizes: whether size-level availability exists for shoes and apparel categories.
- Matching risk: missing GTIN/SKU, near-duplicate titles, brand spelling variants, category drift,
  and products that look like variants of the same model.

## Go Criteria

- At least one offer has a usable product URL, title, source price, and currency.
- Product identity is stable enough to deduplicate by GTIN, SKU, or normalized brand/category/model.
- Categories can be mapped into Kupikupi category slugs without collapsing unrelated products.
- Price and currency values are plausible for Czech market offers.
- Missing sizes are documented if the source only exposes product-level offers.

## No-Go Criteria

- The API key is rejected or the endpoint returns no products.
- Offers are missing product URLs, prices, currencies, or stable source IDs.
- Categories cannot be mapped with enough confidence for the field-test scenario.
- Size-sensitive scenarios are in scope, but the source exposes no size data and no fallback store
  feed is available.
- The sample suggests high duplicate risk that cannot be reviewed through the operator duplicate
  workflow before testers see recommendations.

## Follow-Up

After a successful intake, apply the config, run `source_sync`, inspect sync-run items, review
duplicate candidates, and validate one end-to-end request through WebApp and Telegram notification
delivery.
