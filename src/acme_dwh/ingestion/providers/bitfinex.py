"""Bitfinex public REST adapter (no API key) — the default provider.

The v2 candles endpoint returns rows ordered [MTS, OPEN, CLOSE, HIGH, LOW, VOLUME];
we page by advancing the `start` cursor past the last timestamp until a short page.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Iterator

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from acme_dwh.ingestion.providers.base import RawPoint, SourceDescriptor

log = logging.getLogger(__name__)


def _to_ms(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


class BitfinexExtractor:
    BASE = "https://api-pub.bitfinex.com/v2"

    def __init__(
        self, timeframe: str = "1D", page_limit: int = 1000, client: httpx.Client | None = None
    ) -> None:
        self.timeframe = timeframe
        self.page_limit = page_limit
        self._client = client or httpx.Client(timeout=30.0)
        self._owns_client = client is None
        self.source = SourceDescriptor(
            id="BITFINEX",
            name="Bitfinex",
            description="Bitfinex public exchange OHLCV candles (v2 REST API).",
            endpoint=f"{self.BASE}/candles/trade:{timeframe}:t<SYMBOL>/hist",
        )

    def asset_id(self, symbol: str) -> str:
        return symbol.upper()

    def asset_attributes(self, symbol: str) -> dict[str, str]:
        # common descriptive attributes (Doc 1): every Bitfinex instrument is a crypto pair
        return {"symbol": symbol.upper(), "class": "cryptocurrency", "region": "Global"}

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "BitfinexExtractor":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _get_page(self, url: str, params: dict) -> list:
        resp = self._client.get(url, params=params)
        resp.raise_for_status()
        rows = resp.json()
        if isinstance(rows, list) and rows and rows[0] == "error":
            raise RuntimeError(f"Bitfinex API error: {rows}")
        return rows

    def fetch(
        self, symbol: str, start: date | None = None, end: date | None = None
    ) -> Iterator[RawPoint]:
        url = f"{self.BASE}/candles/trade:{self.timeframe}:t{symbol.upper()}/hist"
        base_params: dict = {"limit": self.page_limit, "sort": 1}
        if end is not None:
            base_params["end"] = _to_ms(end)
        cursor = _to_ms(start) if start is not None else None

        while True:
            params = dict(base_params)
            if cursor is not None:
                params["start"] = cursor
            rows = self._get_page(url, params)
            if not rows:
                break
            for row in rows:
                mts, op, cl, hi, lo, vol = row[0], row[1], row[2], row[3], row[4], row[5]
                business_date = datetime.fromtimestamp(mts / 1000, timezone.utc).date()
                yield RawPoint(
                    business_date,
                    {"open": float(op), "close": float(cl), "high": float(hi),
                     "low": float(lo), "volume": float(vol)},
                )
            if len(rows) < self.page_limit:
                break
            cursor = rows[-1][0] + 1  # next page: past the last candle's timestamp
