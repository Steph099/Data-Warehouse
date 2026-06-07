"""Pure (database-free) helpers shared by the repositories."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterable

from acme_dwh.dal.models import TimeSeriesRecord, Value


def utcnow() -> datetime:
    # naive UTC: the driver returns timestamps as naive UTC, so we keep system_time naive throughout
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_naive_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def split_values(values: dict[str, Value] | None) -> tuple[dict, dict, dict]:
    # bool before int (bool subclasses int) -> stored as text; None skipped
    doubles: dict[str, float] = {}
    ints: dict[str, int] = {}
    texts: dict[str, str] = {}
    for key, val in (values or {}).items():
        if val is None:
            continue
        if isinstance(val, bool):
            texts[key] = str(val)
        elif isinstance(val, float):
            doubles[key] = val
        elif isinstance(val, int):
            ints[key] = val
        else:
            texts[key] = str(val)
    return doubles, ints, texts


def merge_values(doubles: dict | None, ints: dict | None, texts: dict | None) -> dict[str, Value]:
    merged: dict[str, Value] = {}
    merged.update(texts or {})
    merged.update(ints or {})
    merged.update(doubles or {})
    return merged


def years_in_range(start: date, end: date) -> list[int]:
    if end < start:
        return []
    return list(range(start.year, end.year + 1))


def dedup_latest_per_business_date(
    records: Iterable[TimeSeriesRecord], as_of: datetime | None = None
) -> list[TimeSeriesRecord]:
    """Collapse versions to one record per business date, newest date first.

    Input MUST be ordered business_date DESC then system_time DESC (how the schema
    clusters rows). Keeps the first record per date whose system_time <= ``as_of`` —
    the version current at that instant, or the latest when ``as_of`` is None.
    """
    cutoff = as_naive_utc(as_of)
    seen: set[date] = set()
    out: list[TimeSeriesRecord] = []
    for rec in records:
        if cutoff is not None and as_naive_utc(rec.system_time) > cutoff:
            continue
        if rec.business_date in seen:
            continue
        seen.add(rec.business_date)
        out.append(rec)
    return out
