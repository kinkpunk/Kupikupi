import json
import uuid

from sqlalchemy import select

from app.db.seed import seed_mvp_data
from app.domains.stores.models import SourceConfig, Store
from scripts import source_sync
from scripts.source_sync import run_due_source_configs_command, run_source_config_command


async def test_source_sync_script_runs_one_source_config(
    monkeypatch,
    db_session_factory,
    capsys,
) -> None:
    source_config_id = await _seed_demo_source_config(db_session_factory)
    monkeypatch.setattr(source_sync, "async_session_factory", db_session_factory)

    exit_code = await run_source_config_command(source_config_id=str(source_config_id))

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["source_config_id"] == str(source_config_id)
    assert output["status"] == "succeeded"
    assert output["products_seen"] == 2
    assert output["offers_seen"] == 2
    assert output["failed_offers"] == 0


async def test_source_sync_script_runs_due_source_configs(
    monkeypatch,
    db_session_factory,
    capsys,
) -> None:
    source_config_id = await _seed_demo_source_config(db_session_factory)
    monkeypatch.setattr(source_sync, "async_session_factory", db_session_factory)

    exit_code = await run_due_source_configs_command(limit=10)

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["scheduled"] == 1
    assert output["succeeded"] == 1
    assert output["partially_failed"] == 0
    assert output["failed"] == 0
    assert output["runs"][0]["source_config_id"] == str(source_config_id)


async def test_source_sync_script_reports_missing_source_config(
    monkeypatch,
    db_session_factory,
    capsys,
) -> None:
    monkeypatch.setattr(source_sync, "async_session_factory", db_session_factory)

    exit_code = await run_source_config_command(source_config_id=str(uuid.uuid4()))

    assert exit_code == 1
    assert "Source config not found." in capsys.readouterr().out


async def test_source_sync_script_rejects_invalid_uuid(capsys) -> None:
    exit_code = await run_source_config_command(source_config_id="not-a-uuid")

    assert exit_code == 2
    assert "Invalid source config UUID." in capsys.readouterr().out


async def _seed_demo_source_config(db_session_factory) -> uuid.UUID:
    async with db_session_factory() as session:
        await seed_mvp_data(session)
        footshop = await session.scalar(select(Store).where(Store.name == "Footshop"))
        assert footshop is not None
        source_config = await session.scalar(
            select(SourceConfig).where(
                SourceConfig.store_id == footshop.id,
                SourceConfig.source_type == "static_json",
            )
        )
        assert source_config is not None
        source_config_id = source_config.id
        await session.commit()
    return source_config_id
