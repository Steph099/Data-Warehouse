"""Repository for time-series Data — where the bi-temporal read rules live."""
from __future__ import annotations

from datetime import date, datetime
from typing import Sequence

from cassandra.cluster import Session
from cassandra.concurrent import execute_concurrent_with_args

from acme_dwh.dal._mapping import (
    dedup_latest_per_business_date,
    merge_values,
    split_values,
    utcnow,
    years_in_range,
)
from acme_dwh.dal.models import TimeSeriesRecord
from acme_dwh.dal.repository import WarehouseRepository
from acme_dwh.dal.session import get_session

DataKey = tuple[str, str, int]  # (asset_id, data_source_id, business_date_year)

_COLUMNS = "business_date, system_time, values_double, values_int, values_text, deleted"


class TimeSeriesRepository(WarehouseRepository[TimeSeriesRecord, DataKey]):
    def __init__(self, session: Session | None = None) -> None:
        self.session = session or get_session()
        self._insert = self.session.prepare(
            "INSERT INTO data (asset_id, data_source_id, business_date_year, business_date, "
            "system_time, values_double, values_int, values_text, deleted) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        self._select_range = self.session.prepare(
            f"SELECT {_COLUMNS} FROM data WHERE asset_id = ? AND data_source_id = ? "
            "AND business_date_year = ? AND business_date >= ? AND business_date < ?"
        )
        self._select_partition_latest = self.session.prepare(
            f"SELECT {_COLUMNS} FROM data WHERE asset_id = ? AND data_source_id = ? "
            "AND business_date_year = ? LIMIT 1"
        )
        self._select_partition_all = self.session.prepare(
            f"SELECT {_COLUMNS} FROM data WHERE asset_id = ? AND data_source_id = ? "
            "AND business_date_year = ?"
        )

    def _params(self, rec: TimeSeriesRecord) -> tuple:
        doubles, ints, texts = split_values(rec.values)
        return (
            rec.asset_id, rec.data_source_id, rec.business_date.year, rec.business_date,
            rec.system_time, doubles, ints, texts, rec.deleted,
        )

    def save(self, entity: TimeSeriesRecord) -> TimeSeriesRecord:
        self.session.execute(self._insert, self._params(entity))
        return entity

    def save_many(self, records: Sequence[TimeSeriesRecord], concurrency: int = 50) -> int:
        # tolerate partial failures so a job can be retried/resumed; return rows actually written
        params = [self._params(r) for r in records]
        results = execute_concurrent_with_args(
            self.session, self._insert, params, concurrency=concurrency, raise_on_first_error=False
        )
        return sum(1 for ok, _ in results if ok)

    def delete(self, key: DataKey, business_date: date, valid_from: datetime | None = None) -> None:
        asset_id, data_source_id, _year = key
        self.save(
            TimeSeriesRecord(asset_id, data_source_id, business_date, valid_from or utcnow(), {}, deleted=True)
        )

    def delete_all(self, key: DataKey) -> None:
        asset_id, data_source_id, year = key
        self.session.execute(
            "DELETE FROM data WHERE asset_id = %s AND data_source_id = %s AND business_date_year = %s",
            (asset_id, data_source_id, year),
        )

    def find_latest(self, key: DataKey) -> TimeSeriesRecord | None:
        asset_id, data_source_id, year = key
        row = self.session.execute(self._select_partition_latest, (asset_id, data_source_id, year)).one()
        return self._to_record(asset_id, data_source_id, row) if row else None

    def find_all(self, key: DataKey) -> list[TimeSeriesRecord]:
        asset_id, data_source_id, year = key
        rows = self.session.execute(self._select_partition_all, (asset_id, data_source_id, year))
        return [self._to_record(asset_id, data_source_id, r) for r in rows]

    def find_range(
        self,
        asset_id: str,
        data_source_id: str,
        start: date,
        end: date,
        as_of: datetime | None = None,
        include_deleted: bool = False,
    ) -> list[TimeSeriesRecord]:
        """records in [start, end), newest first, latest version per date (or as of ``as_of``)."""
        records: list[TimeSeriesRecord] = []
        # descending years keep the merged sequence business_date DESC and contiguous per date
        for year in sorted(years_in_range(start, end), reverse=True):
            rows = self.session.execute(self._select_range, (asset_id, data_source_id, year, start, end))
            records.extend(self._to_record(asset_id, data_source_id, r) for r in rows)
        latest = dedup_latest_per_business_date(records, as_of=as_of)
        return latest if include_deleted else [r for r in latest if not r.deleted]

    def _to_record(self, asset_id: str, data_source_id: str, row) -> TimeSeriesRecord:
        return TimeSeriesRecord(
            asset_id=asset_id,
            data_source_id=data_source_id,
            business_date=_to_pydate(row.business_date),
            system_time=row.system_time,
            values=merge_values(row.values_double, row.values_int, row.values_text),
            deleted=bool(row.deleted),
        )


def _to_pydate(value) -> date:
    # Cassandra DATE -> datetime.date (driver returns cassandra.util.Date)
    if isinstance(value, date):
        return value
    if hasattr(value, "date"):
        return value.date()
    return value
