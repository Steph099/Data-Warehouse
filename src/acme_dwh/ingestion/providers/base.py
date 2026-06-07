"""Provider-agnostic extraction contract."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterator, Protocol, runtime_checkable


@dataclass(frozen=True)
class SourceDescriptor:
    id: str
    name: str
    description: str
    endpoint: str = ""


@dataclass
class RawPoint:
    business_date: date
    values: dict[str, float | int | str] = field(default_factory=dict)


@runtime_checkable
class Extractor(Protocol):
    """A provider adapter: describes its source and streams paged points for a symbol."""

    source: SourceDescriptor

    def asset_id(self, symbol: str) -> str: ...

    def fetch(
        self, symbol: str, start: date | None = None, end: date | None = None
    ) -> Iterator[RawPoint]: ...
