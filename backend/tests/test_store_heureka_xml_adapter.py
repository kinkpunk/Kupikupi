from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select

from app.domains.fx.models import FxRate
from app.domains.offers.models import Offer
from app.domains.stores.models import SourceConfig, Store
from app.domains.stores.sync import run_source_sync
from app.integrations.stores.heureka_xml import HeurekaXmlSourceAdapter
from app.integrations.stores.registry import adapter_from_source_config

HEUREKA_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<SHOP>
  <SHOPITEM>
    <ITEM_ID>nb-1080-green-42</ITEM_ID>
    <ITEMGROUP_ID>nb-1080</ITEMGROUP_ID>
    <PRODUCTNAME>New Balance Fresh Foam 1080 Green EU 42</PRODUCTNAME>
    <PRODUCT>New Balance Fresh Foam 1080</PRODUCT>
    <URL>https://shop.example.test/nb-1080-green-42</URL>
    <IMGURL>https://shop.example.test/nb-1080.jpg</IMGURL>
    <PRICE_VAT>3290</PRICE_VAT>
    <MANUFACTURER>New Balance</MANUFACTURER>
    <CATEGORYTEXT>Heureka.cz | Obleceni a moda | Obuv | Bezecke boty</CATEGORYTEXT>
    <EAN>1234567890123</EAN>
    <DELIVERY_DATE>0</DELIVERY_DATE>
    <PARAM><PARAM_NAME>Velikost</PARAM_NAME><VAL>42</VAL></PARAM>
    <PARAM><PARAM_NAME>Barva</PARAM_NAME><VAL>zelena</VAL></PARAM>
  </SHOPITEM>
  <SHOPITEM>
    <ITEM_ID>nb-1080-blue-41</ITEM_ID>
    <ITEMGROUP_ID>nb-1080</ITEMGROUP_ID>
    <PRODUCTNAME>New Balance Fresh Foam 1080 Blue EU 41</PRODUCTNAME>
    <PRODUCT>New Balance Fresh Foam 1080</PRODUCT>
    <URL>https://shop.example.test/nb-1080-blue-41</URL>
    <PRICE_VAT>3390,50</PRICE_VAT>
    <MANUFACTURER>New Balance</MANUFACTURER>
    <CATEGORYTEXT>Heureka.cz | Obleceni a moda | Obuv | Bezecke boty</CATEGORYTEXT>
    <DELIVERY_DATE>7</DELIVERY_DATE>
    <PARAM><PARAM_NAME>Velikost</PARAM_NAME><VAL>41</VAL></PARAM>
    <PARAM><PARAM_NAME>Barva</PARAM_NAME><VAL>modra</VAL></PARAM>
  </SHOPITEM>
</SHOP>
"""


def _source_config() -> SourceConfig:
    return SourceConfig(
        source_type="heureka_xml",
        endpoint_url="https://shop.example.test/heureka.xml",
        active=True,
        settings={
            "category_map": {
                "Bezecke boty": {
                    "slug": "running-shoes",
                    "name": "Running Shoes",
                }
            },
            "source_currency": "CZK",
            "size_system": "EU",
        },
    )


async def test_heureka_xml_adapter_maps_products_variants_and_availability() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://shop.example.test/heureka.xml"
        return httpx.Response(200, content=HEUREKA_XML)

    source_config = _source_config()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        records = await HeurekaXmlSourceAdapter(
            source_config,
            client=client,
        ).fetch_offers()

    assert len(records) == 2
    assert records[0].external_id == "nb-1080-green-42"
    assert records[0].source_price == 3290
    assert records[0].source_currency == "CZK"
    assert records[0].availability == "in_stock"
    assert records[0].sizes == [
        {
            "size_value": "42",
            "size_system": "EU",
            "color": "zelena",
            "in_stock": True,
        }
    ]
    assert records[0].product is not None
    assert records[0].product.external_product_id == "nb-1080"
    assert records[0].product.category_slug == "running-shoes"
    assert records[1].availability == "limited"
    assert records[1].source_price == 3390.5


def test_registry_returns_heureka_xml_adapter() -> None:
    assert isinstance(adapter_from_source_config(_source_config()), HeurekaXmlSourceAdapter)


async def test_heureka_xml_source_sync_imports_czk_offer(db_session_factory) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=HEUREKA_XML)

    async with db_session_factory() as session:
        store = Store(name="Heureka XML Store", country="CZ", url="https://shop.example.test")
        source_config = _source_config()
        source_config.store = store
        session.add_all(
            [
                store,
                source_config,
                FxRate(
                    currency="CZK",
                    rate_to_eur=0.040817,
                    source="test",
                    valid_at=datetime(2026, 6, 14, tzinfo=UTC),
                ),
            ]
        )
        await session.flush()

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            sync_run = await run_source_sync(
                session,
                adapter=HeurekaXmlSourceAdapter(source_config, client=client),
                store_id=store.id,
                source_config_id=source_config.id,
            )
        await session.commit()

        offers = list((await session.execute(select(Offer).order_by(Offer.external_id))).scalars())

    assert sync_run.status == "succeeded"
    assert sync_run.products_seen == 1
    assert sync_run.offers_seen == 2
    assert len(offers) == 2
    assert float(offers[1].eur_price) == 134.29


async def test_heureka_xml_adapter_rejects_dtd() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b'<!DOCTYPE SHOP [<!ENTITY x "value">]><SHOP></SHOP>',
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="DTD"):
            await HeurekaXmlSourceAdapter(_source_config(), client=client).fetch_offers()
