"""FastAPI dependencies: cached repository singletons.

Handlers are sync ``def`` so FastAPI runs them in a threadpool — the blocking
Cassandra driver never stalls the event loop. Each repo connects on first use.
"""
from __future__ import annotations

from functools import lru_cache

from acme_dwh.dal.analytics_repository import AnalyticsRepository
from acme_dwh.dal.asset_repository import AssetRepository
from acme_dwh.dal.data_source_repository import DataSourceRepository
from acme_dwh.dal.timeseries_repository import TimeSeriesRepository


@lru_cache
def get_asset_repo() -> AssetRepository:
    return AssetRepository()


@lru_cache
def get_analytics_repo() -> AnalyticsRepository:
    return AnalyticsRepository()


@lru_cache
def get_data_source_repo() -> DataSourceRepository:
    return DataSourceRepository()


@lru_cache
def get_timeseries_repo() -> TimeSeriesRepository:
    return TimeSeriesRepository()
