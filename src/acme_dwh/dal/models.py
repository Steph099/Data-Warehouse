"""Storage-agnostic domain models used across the platform."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

Value = float | int | str


@dataclass
class Asset:
    id: str
    system_time: datetime
    name: str | None = None
    description: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    deleted: bool = False


@dataclass
class DataSource:
    id: str
    system_time: datetime
    name: str | None = None
    description: str | None = None
    attributes: set[str] = field(default_factory=set)  # indicator names this source supplies
    deleted: bool = False


@dataclass
class TimeSeriesRecord:
    """One measurement. business_date is valid time; system_time is transaction time."""

    asset_id: str
    data_source_id: str
    business_date: date
    system_time: datetime
    values: dict[str, Value] = field(default_factory=dict)
    deleted: bool = False

    @property
    def business_date_year(self) -> int:
        return self.business_date.year
