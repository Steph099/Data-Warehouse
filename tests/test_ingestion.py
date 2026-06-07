"""Offline ingestion tests: provider parsing/pagination (mocked HTTP) + transform."""
from __future__ import annotations

from datetime import date, datetime

import httpx
import respx

from acme_dwh.ingestion.providers.base import RawPoint
from acme_dwh.ingestion.providers.bitfinex import BitfinexExtractor
from acme_dwh.ingestion.transform import derive_attribute_names, to_timeseries_records

_CANDLES_URL = "https://api-pub.bitfinex.com/v2/candles"


@respx.mock
def test_bitfinex_parses_candles_and_follows_pagination():
    # Bitfinex rows: [MTS, OPEN, CLOSE, HIGH, LOW, VOLUME]
    page1 = [
        [1577836800000, 7200.0, 7300.0, 7400.0, 7100.0, 1000.0],  # 2020-01-01
        [1577923200000, 7300.0, 7350.0, 7450.0, 7250.0, 1100.0],  # 2020-01-02
    ]
    page2 = [[1578009600000, 7350.0, 7400.0, 7500.0, 7300.0, 1200.0]]  # 2020-01-03
    route = respx.route(method="GET", url__startswith=_CANDLES_URL)
    route.side_effect = [httpx.Response(200, json=page1), httpx.Response(200, json=page2)]

    ext = BitfinexExtractor(timeframe="1D", page_limit=2)  # full page -> must request page 2
    points = list(ext.fetch("BTCUSD"))

    assert route.call_count == 2  # paged until a short page was returned
    assert len(points) == 3
    assert points[0].business_date == date(2020, 1, 1)
    assert points[0].values["open"] == 7200.0  # MTS,open,close,...
    assert points[0].values["close"] == 7300.0
    assert points[0].values["high"] == 7400.0
    assert points[2].business_date == date(2020, 1, 3)


@respx.mock
def test_bitfinex_error_payload_raises():
    route = respx.route(method="GET", url__startswith=_CANDLES_URL)
    route.return_value = httpx.Response(200, json=["error", 10020, "limit: invalid"])
    ext = BitfinexExtractor(page_limit=2)
    try:
        list(ext.fetch("BTCUSD"))
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "Bitfinex API error" in str(exc)


def test_derive_attribute_names_union():
    points = [
        RawPoint(date(2020, 1, 1), {"open": 1.0, "close": 2.0}),
        RawPoint(date(2020, 1, 2), {"open": 1.0, "volume": 5.0}),
    ]
    assert derive_attribute_names(points) == {"open", "close", "volume"}


def test_to_timeseries_records_stamps_identity_and_time():
    points = [RawPoint(date(2020, 1, 1), {"open": 1.0})]
    st = datetime(2020, 1, 2, 3, 4, 5)
    recs = to_timeseries_records("BTCUSD", "BITFINEX", points, st)
    assert len(recs) == 1
    r = recs[0]
    assert (r.asset_id, r.data_source_id, r.business_date, r.system_time) == (
        "BTCUSD",
        "BITFINEX",
        date(2020, 1, 1),
        st,
    )
    assert r.values == {"open": 1.0}
