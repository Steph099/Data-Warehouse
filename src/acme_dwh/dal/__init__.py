"""Data Access Layer — the single source of truth for all CQL.

Importing this package first applies the cassandra-driver compatibility shim so
that ``cassandra.cluster`` can be imported on Windows + CPython >= 3.12.
"""
from acme_dwh.dal import _compat

_compat.apply()
