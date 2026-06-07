"""Repository for DataSource (serves list + details)."""
from __future__ import annotations

from datetime import datetime

from cassandra.cluster import Session

from acme_dwh.dal._mapping import utcnow
from acme_dwh.dal.models import DataSource
from acme_dwh.dal.repository import WarehouseRepository
from acme_dwh.dal.session import get_session

_BUCKET = "ALL"


class DataSourceRepository(WarehouseRepository[DataSource, str]):
    def __init__(self, session: Session | None = None) -> None:
        self.session = session or get_session()
        self._insert = self.session.prepare(
            "INSERT INTO data_source (id, system_time, name, description, attributes, deleted) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        )
        self._insert_id = self.session.prepare("INSERT INTO data_source_ids (bucket, id) VALUES (?, ?)")
        self._select_latest = self.session.prepare(
            "SELECT id, system_time, name, description, attributes, deleted "
            "FROM data_source WHERE id = ? LIMIT 1"
        )
        self._select_all = self.session.prepare(
            "SELECT id, system_time, name, description, attributes, deleted FROM data_source WHERE id = ?"
        )
        self._select_ids = self.session.prepare("SELECT id FROM data_source_ids WHERE bucket = ? LIMIT ?")

    def save(self, entity: DataSource) -> DataSource:
        self.session.execute(
            self._insert,
            (entity.id, entity.system_time, entity.name, entity.description,
             set(entity.attributes or set()), entity.deleted),
        )
        self.session.execute(self._insert_id, (_BUCKET, entity.id))
        return entity

    def delete(self, key: str, valid_from: datetime | None = None) -> None:
        self.save(DataSource(id=key, system_time=valid_from or utcnow(), deleted=True))

    def delete_all(self, key: str) -> None:
        self.session.execute("DELETE FROM data_source WHERE id = %s", (key,))

    def find_latest(self, key: str) -> DataSource | None:
        row = self.session.execute(self._select_latest, (key,)).one()
        return _to_data_source(row) if row else None

    def find_all(self, key: str) -> list[DataSource]:
        return [_to_data_source(r) for r in self.session.execute(self._select_all, (key,))]

    def list_ids(self, limit: int = 20, offset: int = 0) -> list[str]:
        rows = self.session.execute(self._select_ids, (_BUCKET, offset + limit))
        return [r.id for r in rows][offset : offset + limit]


def _to_data_source(row) -> DataSource:
    return DataSource(
        id=row.id,
        system_time=row.system_time,
        name=row.name,
        description=row.description,
        attributes=set(row.attributes or set()),
        deleted=bool(row.deleted),
    )
