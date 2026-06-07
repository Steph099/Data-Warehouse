"""Tests for the schema loader (no Cassandra needed)."""
from __future__ import annotations

from acme_dwh.db.init_db import SCHEMA_FILE, split_statements


def test_split_statements_ignores_semicolons_in_comments():
    cql = (
        "-- a comment with a semicolon; and more\n"
        "CREATE TABLE foo (id int PRIMARY KEY);\n"
        "-- another; tricky comment\n"
        "CREATE TABLE bar (id int PRIMARY KEY);\n"
    )
    stmts = split_statements(cql)
    assert len(stmts) == 2
    assert stmts[0].startswith("CREATE TABLE foo")
    assert stmts[1].startswith("CREATE TABLE bar")


def test_real_schema_parses_to_seven_create_tables():
    stmts = split_statements(SCHEMA_FILE.read_text(encoding="utf-8"))
    assert len(stmts) == 7  # asset(+_ids), data_source(+_ids), data, totals, regression_results
    assert all(s.upper().startswith("CREATE TABLE") for s in stmts)
    # a 'WITH CLUSTERING' clause must never get split off into its own statement
    assert not any(s.upper().startswith("CLUSTERING") for s in stmts)
