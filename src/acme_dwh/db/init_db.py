"""Create the keyspace and apply the schema (idempotent). Run: acme-init-db"""
from __future__ import annotations

import logging
from pathlib import Path

from acme_dwh.config import get_settings
from acme_dwh.dal.session import build_cluster

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("init_db")

SCHEMA_FILE = Path(__file__).resolve().parent / "schema.cql"


def split_statements(cql: str) -> list[str]:
    # Strip full-line comments first, so a ';' inside a comment cannot split a statement.
    code = "\n".join(ln for ln in cql.splitlines() if not ln.strip().startswith("--"))
    return [stmt.strip() for stmt in code.split(";") if stmt.strip()]


def main() -> None:
    s = get_settings()
    cluster = build_cluster(s)
    session = cluster.connect()
    session.execute(
        f"CREATE KEYSPACE IF NOT EXISTS {s.cassandra_keyspace} WITH replication = "
        f"{{'class': 'SimpleStrategy', 'replication_factor': {s.cassandra_replication_factor}}}"
    )
    session.set_keyspace(s.cassandra_keyspace)
    statements = split_statements(SCHEMA_FILE.read_text(encoding="utf-8"))
    for stmt in statements:
        session.execute(stmt)
    log.info("Keyspace '%s' ready; applied %d statement(s).", s.cassandra_keyspace, len(statements))
    cluster.shutdown()


if __name__ == "__main__":
    main()
