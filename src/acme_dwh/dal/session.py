"""Cassandra connection management for the DAL."""
from __future__ import annotations

import logging
from functools import lru_cache

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, Session
from cassandra.io.asyncioreactor import AsyncioConnection
from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy

from acme_dwh.config import Settings, get_settings
from acme_dwh.dal import _compat

log = logging.getLogger(__name__)


def build_cluster(settings: Settings | None = None) -> Cluster:
    _compat.ensure_windows_selector_loop()  # asyncio reactor needs a SelectorEventLoop on Windows/3.12+
    s = settings or get_settings()
    auth = (
        PlainTextAuthProvider(username=s.cassandra_username, password=s.cassandra_password or "")
        if s.cassandra_username
        else None
    )
    return Cluster(
        contact_points=s.cassandra_contact_points,
        port=s.cassandra_port,
        auth_provider=auth,
        connection_class=AsyncioConnection,
        protocol_version=5,
        load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc=s.cassandra_local_dc)),
    )


@lru_cache
def get_session() -> Session:
    s = get_settings()
    session = build_cluster(s).connect(s.cassandra_keyspace)
    session.default_fetch_size = 1000
    log.info("Connected to Cassandra keyspace '%s'", s.cassandra_keyspace)
    return session
