from sqlalchemy import func, select

from app.db.seed import seed_mvp_data
from app.domains.fx.models import FxRate
from app.domains.offers.models import Offer, PriceSnapshot
from app.domains.stores.models import SourceConfig, SourceProductMapping, Store
from app.domains.stores.sync import run_source_sync
from app.integrations.stores.registry import adapter_from_source_config


async def test_mvp_seed_creates_demo_source_config_and_syncs_offers(db_session_factory) -> None:
    async with db_session_factory() as session:
        await seed_mvp_data(session)
        await seed_mvp_data(session)

        footshop = await session.scalar(select(Store).where(Store.name == "Footshop"))
        assert footshop is not None

        source_configs = list(
            (
                await session.execute(
                    select(SourceConfig).where(
                        SourceConfig.store_id == footshop.id,
                        SourceConfig.source_type == "static_json",
                    )
                )
            )
            .scalars()
            .all()
        )
        demo_configs = [
            source_config
            for source_config in source_configs
            if (source_config.settings or {}).get("demo") is True
        ]
        assert len(demo_configs) == 1
        demo_config = demo_configs[0]
        assert demo_config.active is True
        assert demo_config.sync_interval_minutes == 60
        assert len((demo_config.settings or {})["records"]) == 2

        fx_rate_count = await session.scalar(
            select(func.count(FxRate.id)).where(FxRate.currency == "CZK")
        )
        assert fx_rate_count == 1

        sync_run = await run_source_sync(
            session,
            adapter=adapter_from_source_config(demo_config),
            store_id=footshop.id,
            source_config_id=demo_config.id,
        )
        await session.commit()

        assert sync_run.status == "succeeded"
        assert sync_run.products_seen == 2
        assert sync_run.offers_seen == 2

    async with db_session_factory() as session:
        offer_count = await session.scalar(select(func.count(Offer.id)))
        snapshot_count = await session.scalar(select(func.count(PriceSnapshot.id)))
        mapping_count = await session.scalar(select(func.count(SourceProductMapping.id)))

        assert offer_count == 2
        assert snapshot_count == 2
        assert mapping_count == 2
