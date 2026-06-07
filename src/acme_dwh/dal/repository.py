"""Generic repository contract (see Project documentation/4-data-access-layer.md)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, Iterable, TypeVar

E = TypeVar("E")
K = TypeVar("K")


class WarehouseRepository(ABC, Generic[E, K]):
    @abstractmethod
    def save(self, entity: E) -> E: ...

    @abstractmethod
    def find_latest(self, key: K) -> E | None: ...

    @abstractmethod
    def find_all(self, key: K) -> Iterable[E]: ...

    @abstractmethod
    def delete(self, key: K, *args, **kwargs) -> None:
        """Temporal delete: append a tombstone version (never an in-place delete)."""

    @abstractmethod
    def delete_all(self, key: K) -> None:
        """Physically drop a partition — maintenance/testing only, not the temporal delete."""
