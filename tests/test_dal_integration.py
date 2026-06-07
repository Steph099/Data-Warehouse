"""DAL integration tests against a live Cassandra.

Auto-skips when Cassandra (with the keyspace/schema) isn't reachable, so the
suite stays green offline. To run for real:

    docker compose up -d cassandra
    python db/init_db.py
    pytest tests/test_dal_integration.py
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest

from acme_dwh.config import get_settings
from acme_dwh.dal.models import Asset, DataSource, TimeSeriesRecord


@pytest.fixture(scope="session")
def session():
    from acme_dwh.dal.session import build_cluster

    s = get_settings()
    try:
        cluster = build_cluster(s)
        sess = cluster.connect(s.cassandra_keyspace)
    except Exception as exc:  # noqa: BLE001 - any connect failure => skip
        pytest.skip(
            f"Cassandra/keyspace not available ({exc}). "
            "Run `docker compose up -d cassandra` and `python db/init_db.py`."
        )
    yield sess
    cluster.shutdown()


def test_asset_save_find_latest_find_all(session):
    from acme_dwh.dal.asset_repository import AssetRepository

    repo = AssetRepository(session)
    aid = f"TEST/ASSET/{uuid4()}"
    try:
        repo.save(Asset(aid, datetime(2023, 1, 1), name="v1", attributes={"x": "1"}))
        repo.save(Asset(aid, datetime(2024, 1, 1), name="v2", attributes={"x": "2"}))

        latest = repo.find_latest(aid)
        assert latest is not None and latest.name == "v2"  # newest version wins

        history = repo.find_all(aid)
        assert [a.name for a in history] == ["v2", "v1"]  # newest first

        assert aid in repo.list_ids(limit=10_000)
    finally:
        repo.delete_all(aid)
        session.execute("DELETE FROM asset_ids WHERE bucket = 'ALL' AND id = %s", (aid,))


def test_data_source_save_find_latest(session):
    from acme_dwh.dal.data_source_repository import DataSourceRepository

    repo = DataSourceRepository(session)
    sid = f"TEST/SRC/{uuid4()}"
    try:
        repo.save(DataSource(sid, datetime(2024, 1, 1), name="src", attributes={"Open", "Close"}))
        latest = repo.find_latest(sid)
        assert latest is not None and latest.attributes == {"Open", "Close"}
    finally:
        repo.delete_all(sid)
        session.execute("DELETE FROM data_source_ids WHERE bucket = 'ALL' AND id = %s", (sid,))


def test_timeseries_latest_asof_and_temporal_delete(session):
    from acme_dwh.dal.timeseries_repository import TimeSeriesRepository

    repo = TimeSeriesRepository(session)
    aid, sid = f"T/{uuid4()}", "TEST/SRC"
    key = (aid, sid, 2022)
    bdate = date(2022, 1, 5)
    try:
        # Two versions of the same business date (an original then a correction).
        repo.save(TimeSeriesRecord(aid, sid, bdate, datetime(2022, 1, 6), {"close": 10.0}))
        repo.save(TimeSeriesRecord(aid, sid, bdate, datetime(2022, 2, 1), {"close": 11.0}))

        latest = repo.find_range(aid, sid, date(2022, 1, 1), date(2022, 2, 1))
        assert len(latest) == 1 and latest[0].values["close"] == 11.0  # correction wins

        # As-of before the correction reproduces the original value (historical correctness).
        as_of = repo.find_range(
            aid, sid, date(2022, 1, 1), date(2022, 2, 1), as_of=datetime(2022, 1, 10)
        )
        assert as_of[0].values["close"] == 10.0

        # Temporal deletion: a tombstone hides the date from current reads...
        repo.delete(key, bdate)
        assert repo.find_range(aid, sid, date(2022, 1, 1), date(2022, 2, 1)) == []

        # ...but past snapshots remain reproducible.
        still = repo.find_range(
            aid, sid, date(2022, 1, 1), date(2022, 2, 1), as_of=datetime(2022, 1, 10)
        )
        assert still[0].values["close"] == 10.0
    finally:
        repo.delete_all(key)
