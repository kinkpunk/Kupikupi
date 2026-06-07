from scripts.smoke_mvp import run_mvp_smoke


async def test_run_mvp_smoke_creates_local_demo_flow(db_session_factory) -> None:
    async with db_session_factory() as session:
        report = await run_mvp_smoke(session)

    assert report.synced_sources == 1
    assert report.imported_offers == 2
    assert report.recommendations == 2
    assert report.deals >= 1
    assert report.notifications_created >= 1
