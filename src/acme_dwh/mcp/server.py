"""Read-only MCP server exposing the warehouse consumption API as tools.

Builds on top of the REST API (it never touches the database directly): each tool
validates inputs, calls the running API, and returns a structured result, preserving
the API's temporal semantics and provenance. Requires the API running (MCP_API_BASE_URL).
Run: acme-mcp  (or python -m acme_dwh.mcp.server)
"""
from __future__ import annotations

import logging
from datetime import date

import httpx
from mcp.server.fastmcp import FastMCP

from acme_dwh.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

mcp = FastMCP("acme-dwh")


def _client() -> httpx.Client:
    return httpx.Client(base_url=settings.mcp_api_base_url, timeout=30.0)


def _validate_page(offset: int, limit: int) -> None:
    if offset < 0:
        raise ValueError("offset must be >= 0")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")


def _require(value: str, name: str) -> str:
    if not value or not str(value).strip():
        raise ValueError(
            f"{name} is required and must be a concrete id "
            "(call list_assets / list_data_sources to obtain one)."
        )
    return str(value).strip()


@mcp.tool()
def list_assets(offset: int = 0, limit: int = 20) -> dict:
    """List financial asset identifiers in the warehouse (paged, alphabetical).

    Page with offset/limit; do not attempt to fetch everything at once.
    Returns: {offset, limit, count, assetIds[]}.
    """
    _validate_page(offset, limit)
    with _client() as client:
        resp = client.get("/assets", params={"offset": offset, "limit": limit})
        resp.raise_for_status()
        ids = resp.json()
    return {"offset": offset, "limit": limit, "count": len(ids), "assetIds": ids}


@mcp.tool()
def get_asset_details(assetId: str) -> dict:
    """Return the latest known details (identity + attributes) for one asset id.
    Raises an error if the asset does not exist.
    """
    assetId = _require(assetId, "assetId")
    with _client() as client:
        resp = client.get(f"/assets/{assetId}")
        if resp.status_code == 404:
            raise ValueError(f"Asset '{assetId}' not found")
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def list_data_sources(offset: int = 0, limit: int = 20) -> dict:
    """List data-source (provider) identifiers (paged, alphabetical).
    Returns: {offset, limit, count, dataSourceIds[]}.
    """
    _validate_page(offset, limit)
    with _client() as client:
        resp = client.get("/data-sources", params={"offset": offset, "limit": limit})
        resp.raise_for_status()
        ids = resp.json()
    return {"offset": offset, "limit": limit, "count": len(ids), "dataSourceIds": ids}


@mcp.tool()
def get_data_source_details(dataSourceId: str) -> dict:
    """Return the latest details for one data source, including the indicator
    attributes it supplies (provenance). Raises an error if it does not exist.
    """
    dataSourceId = _require(dataSourceId, "dataSourceId")
    with _client() as client:
        resp = client.get(f"/data-sources/{dataSourceId}")
        if resp.status_code == 404:
            raise ValueError(f"Data source '{dataSourceId}' not found")
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def get_time_series_data(
    assetId: str,
    dataSourceId: str,
    startBusinessDate: str,
    endBusinessDate: str,
    includeAttributes: bool = False,
) -> dict:
    """Return time-series records for an asset+source over a bounded date range.

    Dates are ISO 'YYYY-MM-DD'. The interval is half-open [start, end): records are
    returned newest business date first, one (latest) version per date, tombstones
    excluded. Large ranges are rejected — request a focused window.
    Returns: {data: {assetId, dataSourceId, records: [{businessDate, values}]}, attributes?}.
    """
    assetId = _require(assetId, "assetId")
    dataSourceId = _require(dataSourceId, "dataSourceId")
    try:
        start = date.fromisoformat(startBusinessDate)
        end = date.fromisoformat(endBusinessDate)
    except ValueError as exc:
        raise ValueError(f"dates must be ISO YYYY-MM-DD: {exc}")
    if end < start:
        raise ValueError("endBusinessDate must be >= startBusinessDate")
    if (end - start).days > settings.max_data_range_days:
        raise ValueError(
            f"Requested range exceeds {settings.max_data_range_days} days; narrow the interval."
        )
    with _client() as client:
        resp = client.get(
            "/data",
            params={
                "assetId": assetId,
                "dataSourceId": dataSourceId,
                "startBusinessDate": startBusinessDate,
                "endBusinessDate": endBusinessDate,
                "includeAttributes": str(includeAttributes).lower(),
            },
        )
        resp.raise_for_status()
        return resp.json()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
