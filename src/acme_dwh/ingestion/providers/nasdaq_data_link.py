"""Nasdaq Data Link (Quandl) Tables API adapter — requires a free API key.

Generic over a datatable (default QDL/BITFINEX); follows cursor pagination via
qopts.cursor_id until meta.next_cursor_id is null.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Iterator

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from acme_dwh.ingestion.providers.base import RawPoint, SourceDescriptor

log = logging.getLogger(__name__)


class NasdaqDataLinkExtractor:
    BASE = "https://data.nasdaq.com/api/v3/datatables"

    def __init__(
        self,
        api_key: str | None,
        database_code: str = "QDL",
        table_code: str = "BITFINEX",
        code_column: str = "code",
        date_column: str = "date",
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Nasdaq Data Link requires an API key. Set NDL_API_KEY in your .env.")
        self.api_key = api_key
        self.database_code = database_code
        self.table_code = table_code
        self.code_column = code_column
        self.date_column = date_column
        self._client = client or httpx.Client(timeout=30.0)
        self._owns_client = client is None
        self.source = SourceDescriptor(
            id=f"NASDAQ-DATA-LINK.{database_code}/{table_code}",
            name="Nasdaq Data Link",
            description=f"Nasdaq Data Link Tables API datatable {database_code}/{table_code}.",
            endpoint=f"{self.BASE}/{database_code}/{table_code}",
        )

    def asset_id(self, symbol: str) -> str:
        return symbol.upper()

    def asset_attributes(self, symbol: str) -> dict[str, str]:
        return {"symbol": symbol.upper(), "class": self.table_code.lower(), "region": "Global"}

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "NasdaqDataLinkExtractor":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _get_page(self, url: str, params: dict) -> dict:
        resp = self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def fetch(
        self, symbol: str, start: date | None = None, end: date | None = None
    ) -> Iterator[RawPoint]:
        url = f"{self.BASE}/{self.database_code}/{self.table_code}.json"
        params: dict = {"api_key": self.api_key, self.code_column: symbol.upper()}
        if start is not None:
            params[f"{self.date_column}.gte"] = start.isoformat()
        if end is not None:
            params[f"{self.date_column}.lt"] = end.isoformat()

        cursor: str | None = None
        while True:
            page_params = dict(params)
            if cursor:
                page_params["qopts.cursor_id"] = cursor
            payload = self._get_page(url, page_params)
            datatable = payload.get("datatable", {})
            columns = [c["name"] for c in datatable.get("columns", [])]
            for row in datatable.get("data", []):
                record = dict(zip(columns, row))
                raw_date = str(record.get(self.date_column, ""))[:10]
                if not raw_date:
                    continue
                values = {
                    k: v
                    for k, v in record.items()
                    if k not in (self.date_column, self.code_column) and v is not None
                }
                yield RawPoint(date.fromisoformat(raw_date), values)
            cursor = (payload.get("meta") or {}).get("next_cursor_id")
            if not cursor:
                break
