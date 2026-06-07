"""End-to-end ingestion against live Cassandra (auto-skips if unavailable).

Uses a fake in-memory extractor (no network) so the test is deterministic, then
verifies the data is queryable through the DAL and that re-running is idempotent.
"""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from acme_dwh.config import get_settings
from acme_dwh.ingestion.load import Ingestor
from acme_dwh.ingestion.providers.base import RawPoint, SourceDescriptor


@pytest.fixture(scope="session")
def repos():
    from acme_dwh.dal.asset_repository import AssetRepository
    from acme_dwh.dal.data_source_repository import DataSourceRepository
    from acme_dwh.dal.session import build_cluster
    from acme_dwh.dal.timeseries_repository import TimeSeriesRepository

    s = get_settings()
    try:
        cluster = build_cluster(s)
        session = cluster.connect(s.cassandra_keyspace)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Cassandra/keyspace not available ({exc}).")
    yield (
        AssetRepository(session),
        DataSourceRepository(session),
        TimeSeriesRepository(session),
        session,
    )
    cluster.shutdown()


class _FakeExtractor:
    def __init__(self, source_id: str, asset_id: str, points: list[RawPoint]):
        self.source = SourceDescriptor(source_id, "Fake", "fake source", "http://fake/endpoint")
        self._asset_id = asset_id
        self._points = points

    def asset_id(self, symbol: str) -> str:
        return self._asset_id

    def fetch(self, symbol: str, start=None, end=None):
        yield from self._points


def test_ingest_end_to_end_and_idempotent(repos):
    assets, sources, ts, session = repos
    suffix = uuid4().hex[:8]
    asset_id, source_id = f"TEST/BTC/{suffix}", f"TEST/SRC/{suffix}"
    points = [
        RawPoint(date(2021, 3, 1), {"open": 10.0, "close": 11.0, "volume": 100.0}),
        RawPoint(date(2021, 3, 2), {"open": 11.0, "close": 12.0, "volume": 120.0}),
    ]
    ingestor = Ingestor(_FakeExtractor(source_id, asset_id, points), assets, sources, ts)
    try:
        stats = ingestor.ingest_symbol("BTCUSD")
        assert stats.fetched == 2 and stats.stored == 2
        assert stats.attributes == ["close", "open", "volume"]

        assert assets.find_latest(asset_id) is not None
        src = sources.find_latest(source_id)
        assert src is not None and {"open", "close", "volume"} <= src.attributes
        assert "endpoint: http://fake/endpoint" in (src.description or "")  # provenance captured

        recs = ts.find_range(asset_id, source_id, date(2021, 1, 1), date(2022, 1, 1))
        assert [r.business_date for r in recs] == [date(2021, 3, 2), date(2021, 3, 1)]
        assert recs[0].values["close"] == 12.0

        # Re-run: metadata must NOT be re-versioned; reads stay correct.
        ingestor.ingest_symbol("BTCUSD")
        assert len(assets.find_all(asset_id)) == 1
        assert len(sources.find_all(source_id)) == 1
        recs2 = ts.find_range(asset_id, source_id, date(2021, 1, 1), date(2022, 1, 1))
        assert len(recs2) == 2 and recs2[0].values["close"] == 12.0
    finally:
        ts.delete_all((asset_id, source_id, 2021))
        assets.delete_all(asset_id)
        sources.delete_all(source_id)
        session.execute("DELETE FROM asset_ids WHERE bucket = 'ALL' AND id = %s", (asset_id,))
        session.execute("DELETE FROM data_source_ids WHERE bucket = 'ALL' AND id = %s", (source_id,))
