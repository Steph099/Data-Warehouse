"""Loading stage: persist transformed data + provenance through the DAL."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime

from acme_dwh.dal._mapping import utcnow
from acme_dwh.dal.asset_repository import AssetRepository
from acme_dwh.dal.data_source_repository import DataSourceRepository
from acme_dwh.dal.models import Asset, DataSource
from acme_dwh.dal.timeseries_repository import TimeSeriesRepository
from acme_dwh.ingestion.providers.base import Extractor
from acme_dwh.ingestion.transform import derive_attribute_names, to_timeseries_records

log = logging.getLogger(__name__)


@dataclass
class IngestStats:
    symbol: str
    asset_id: str
    data_source_id: str
    fetched: int = 0
    transformed: int = 0
    stored: int = 0
    skipped: int = 0
    failed: int = 0
    attributes: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"[{self.symbol}] asset={self.asset_id} source={self.data_source_id} "
            f"fetched={self.fetched} transformed={self.transformed} stored={self.stored} "
            f"skipped={self.skipped} failed={self.failed} attributes={self.attributes}"
        )


class Ingestor:
    def __init__(
        self,
        extractor: Extractor,
        asset_repo: AssetRepository | None = None,
        source_repo: DataSourceRepository | None = None,
        ts_repo: TimeSeriesRepository | None = None,
    ) -> None:
        self.extractor = extractor
        self.assets = asset_repo or AssetRepository()
        self.sources = source_repo or DataSourceRepository()
        self.ts = ts_repo or TimeSeriesRepository()

    def ingest_symbol(
        self, symbol: str, start: date | None = None, end: date | None = None
    ) -> IngestStats:
        source = self.extractor.source
        asset_id = self.extractor.asset_id(symbol)
        log.info("Fetching %s from %s ...", symbol, source.id)

        points = list(self.extractor.fetch(symbol, start, end))  # adapter handles paging
        attributes = derive_attribute_names(points)
        now = utcnow()

        self._ensure_asset(asset_id, self._asset_attributes(symbol, asset_id), now)
        self._ensure_source(source, attributes, now)

        records = to_timeseries_records(asset_id, source.id, points, now)
        stored = self.ts.save_many(records) if records else 0
        stats = IngestStats(
            symbol=symbol,
            asset_id=asset_id,
            data_source_id=source.id,
            fetched=len(points),
            transformed=len(records),
            stored=stored,
            skipped=len(points) - len(records),
            failed=len(records) - stored,
            attributes=sorted(attributes),
        )
        log.info("%s", stats)
        return stats

    def _asset_attributes(self, symbol: str, asset_id: str) -> dict[str, str]:
        # common descriptive attributes (class/region/symbol) when the provider exposes them
        provider_attrs = getattr(self.extractor, "asset_attributes", None)
        return provider_attrs(symbol) if callable(provider_attrs) else {"symbol": asset_id}

    # Metadata writes are idempotent: a new version is appended only when content changes,
    # so re-running ingestion does not bloat versions.
    def _ensure_asset(self, asset_id: str, attributes: dict[str, str], now: datetime) -> None:
        description = f"Auto-registered from {self.extractor.source.id}"
        latest = self.assets.find_latest(asset_id)
        if latest is None or latest.attributes != attributes or latest.description != description:
            self.assets.save(
                Asset(id=asset_id, system_time=now, name=asset_id,
                      description=description, attributes=attributes)
            )

    def _ensure_source(self, source, attributes: set[str], now: datetime) -> None:
        latest = self.sources.find_latest(source.id)
        merged = set(attributes) | (latest.attributes if latest else set())
        description = f"{source.description} | endpoint: {source.endpoint}"
        if latest is None or latest.attributes != merged or latest.description != description:
            self.sources.save(
                DataSource(id=source.id, system_time=now, name=source.name,
                           description=description, attributes=merged)
            )
