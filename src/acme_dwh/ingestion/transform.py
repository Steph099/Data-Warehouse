"""Transformation stage: provider RawPoints -> canonical domain objects (pure)."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from acme_dwh.dal.models import TimeSeriesRecord
from acme_dwh.ingestion.providers.base import RawPoint


def derive_attribute_names(points: Iterable[RawPoint]) -> set[str]:
    # attribute names are derived from incoming data, not hard-coded, so new indicators flow through
    names: set[str] = set()
    for point in points:
        names.update(point.values.keys())
    return names


def to_timeseries_records(
    asset_id: str, data_source_id: str, points: Iterable[RawPoint], system_time: datetime
) -> list[TimeSeriesRecord]:
    return [
        TimeSeriesRecord(
            asset_id=asset_id,
            data_source_id=data_source_id,
            business_date=point.business_date,
            system_time=system_time,
            values=dict(point.values),
        )
        for point in points
        if point.values  # skip points carrying no indicators
    ]
