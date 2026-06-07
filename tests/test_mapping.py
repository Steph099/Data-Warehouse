"""Unit tests for the database-free DAL helpers (no Cassandra required)."""
from __future__ import annotations

from datetime import date, datetime

from acme_dwh.dal._mapping import (
    dedup_latest_per_business_date,
    merge_values,
    split_values,
    years_in_range,
)
from acme_dwh.dal.models import TimeSeriesRecord


def test_split_values_by_type():
    doubles, ints, texts = split_values(
        {"open": 35.0, "volume": 1200, "color": "gray", "halted": True, "missing": None}
    )
    assert doubles == {"open": 35.0}
    assert ints == {"volume": 1200}
    # bool is an int subclass but must be stored as text; None is skipped entirely.
    assert texts == {"color": "gray", "halted": "True"}


def test_merge_values_roundtrip():
    values = {"open": 35.0, "volume": 1200, "color": "gray"}
    doubles, ints, texts = split_values(values)
    assert merge_values(doubles, ints, texts) == values


def test_merge_values_handles_none_maps():
    assert merge_values(None, None, None) == {}


def test_years_in_range():
    assert years_in_range(date(2020, 1, 1), date(2020, 6, 1)) == [2020]
    assert years_in_range(date(2019, 11, 1), date(2021, 2, 1)) == [2019, 2020, 2021]
    assert years_in_range(date(2021, 1, 1), date(2020, 1, 1)) == []  # end < start


def _rec(d: date, st: datetime, deleted: bool = False) -> TimeSeriesRecord:
    return TimeSeriesRecord("AAA", "SRC", d, st, {"close": 1.0}, deleted)


# Rows as the DB returns them: business_date DESC, then system_time DESC.
D2, D1 = date(2021, 1, 2), date(2021, 1, 1)
T_LOW, T_HIGH = datetime(2021, 1, 10), datetime(2021, 6, 10)
ROWS = [
    _rec(D2, datetime(2021, 7, 1)),  # D2 newest
    _rec(D2, datetime(2021, 2, 1)),  # D2 older
    _rec(D1, datetime(2021, 6, 1)),  # D1 newest
    _rec(D1, datetime(2021, 1, 1)),  # D1 older
]


def test_dedup_keeps_latest_version_per_date_newest_first():
    out = dedup_latest_per_business_date(ROWS)
    assert [r.business_date for r in out] == [D2, D1]  # newest business date first
    assert [r.system_time for r in out] == [datetime(2021, 7, 1), datetime(2021, 6, 1)]


def test_dedup_as_of_reproduces_past_snapshot():
    # As of 2021-03-01: D2's 07-01 version didn't exist yet -> see 02-01;
    # D1's 06-01 version didn't exist yet -> see 01-01.
    out = dedup_latest_per_business_date(ROWS, as_of=datetime(2021, 3, 1))
    assert [r.system_time for r in out] == [datetime(2021, 2, 1), datetime(2021, 1, 1)]


def test_dedup_as_of_before_any_data_is_empty():
    assert dedup_latest_per_business_date(ROWS, as_of=datetime(2019, 1, 1)) == []
