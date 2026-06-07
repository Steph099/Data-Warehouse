"""API tests via FastAPI TestClient against live Cassandra (auto-skips if down).

Seeds a unique asset/source/series, exercises + temporal/pagination rules,
then cleans up.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from acme_dwh.config import get_settings
from acme_dwh.dal.models import Asset, DataSource, TimeSeriesRecord


@pytest.fixture(scope="module")
def api():
    s = get_settings()
    try:
        from acme_dwh.dal.session import build_cluster

        cluster = build_cluster(s)
        session = cluster.connect(s.cassandra_keyspace)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Cassandra/keyspace not available ({exc}).")

    from acme_dwh.dal.asset_repository import AssetRepository
    from acme_dwh.dal.data_source_repository import DataSourceRepository
    from acme_dwh.dal.timeseries_repository import TimeSeriesRepository

    assets = AssetRepository(session)
    sources = DataSourceRepository(session)
    ts = TimeSeriesRepository(session)

    suffix = uuid4().hex[:8]
    aid, sid = f"QDL/TEST/{suffix}", f"TESTSRC/{suffix}"  # slash in id exercises {:path}
    now = datetime(2024, 1, 1)
    assets.save(Asset(aid, now, name="API Test Asset", attributes={"region": "US"}))
    sources.save(DataSource(sid, now, name="API Src", description="d", attributes={"open", "close"}))
    ts.save_many(
        [
            TimeSeriesRecord(aid, sid, date(2024, 1, 2), now, {"open": 1.0, "close": 2.0}),
            TimeSeriesRecord(aid, sid, date(2024, 1, 3), now, {"open": 2.0, "close": 3.0}),
            TimeSeriesRecord(aid, sid, date(2024, 1, 4), now, {"open": 3.0, "close": 4.0}),
        ]
    )

    from acme_dwh.api.main import app

    client = TestClient(app)
    try:
        yield client, s.api_base_path, aid, sid
    finally:
        ts.delete_all((aid, sid, 2024))
        assets.delete_all(aid)
        sources.delete_all(sid)
        session.execute("DELETE FROM asset_ids WHERE bucket = 'ALL' AND id = %s", (aid,))
        session.execute("DELETE FROM data_source_ids WHERE bucket = 'ALL' AND id = %s", (sid,))
        cluster.shutdown()


def test_health(api):
    client, *_ = api
    assert client.get("/health").json() == {"status": "ok"}


def test_q1_list_assets(api):
    client, base, aid, _sid = api
    resp = client.get(f"{base}/assets", params={"limit": 1000})
    assert resp.status_code == 200 and aid in resp.json()


def test_q2_asset_detail_and_404(api):
    client, base, aid, _sid = api
    ok = client.get(f"{base}/assets/{aid}")
    assert ok.status_code == 200
    body = ok.json()
    assert body["id"] == aid and body["attributes"]["region"] == "US"

    assert client.get(f"{base}/assets/DOES/NOT/EXIST").status_code == 404


def test_q4_data_source_detail(api):
    client, base, _aid, sid = api
    resp = client.get(f"{base}/data-sources/{sid}")
    assert resp.status_code == 200
    assert set(resp.json()["attributes"]) >= {"open", "close"}


def test_q5_data_half_open_newest_first_with_attributes(api):
    client, base, aid, sid = api
    resp = client.get(
        f"{base}/data",
        params={
            "assetId": aid,
            "dataSourceId": sid,
            "startBusinessDate": "2024-01-02",
            "endBusinessDate": "2024-01-04",  # exclusive -> 01-04 omitted
            "includeAttributes": "true",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    dates = [r["businessDate"] for r in body["data"]["records"]]
    assert dates == ["2024-01-03", "2024-01-02"]  # newest first, half-open
    assert body["data"]["assetId"] == aid
    assert set(body["attributes"]) == {"open", "close"}


def test_q5_rejects_inverted_range(api):
    client, base, aid, sid = api
    resp = client.get(
        f"{base}/data",
        params={
            "assetId": aid,
            "dataSourceId": sid,
            "startBusinessDate": "2024-02-01",
            "endBusinessDate": "2024-01-01",
        },
    )
    assert resp.status_code == 400
