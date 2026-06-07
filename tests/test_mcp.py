"""MCP server tool tests — validation + API delegation (HTTP mocked, no live deps)."""
from __future__ import annotations

import httpx
import pytest
import respx

from acme_dwh.config import get_settings
from acme_dwh.mcp import server

BASE = get_settings().mcp_api_base_url


@respx.mock
def test_list_assets_shapes_response():
    respx.route(method="GET", url__startswith=f"{BASE}/assets").mock(
        return_value=httpx.Response(200, json=["BTCUSD", "ETHUSD"])
    )
    assert server.list_assets(offset=0, limit=20) == {
        "offset": 0,
        "limit": 20,
        "count": 2,
        "assetIds": ["BTCUSD", "ETHUSD"],
    }


def test_list_assets_validates_paging():
    with pytest.raises(ValueError):
        server.list_assets(limit=0)
    with pytest.raises(ValueError):
        server.list_assets(limit=5000)
    with pytest.raises(ValueError):
        server.list_assets(offset=-1)


@respx.mock
def test_get_asset_details_404_is_clear_error():
    respx.route(method="GET", url__startswith=f"{BASE}/assets/NOPE").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    with pytest.raises(ValueError, match="not found"):
        server.get_asset_details("NOPE")


@respx.mock
def test_get_time_series_forwards_params():
    route = respx.route(method="GET", url__startswith=f"{BASE}/data").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {"assetId": "BTCUSD", "dataSourceId": "BITFINEX", "records": []},
                "attributes": [],
            },
        )
    )
    out = server.get_time_series_data(
        "BTCUSD", "BITFINEX", "2024-01-01", "2024-01-10", includeAttributes=True
    )
    assert out["data"]["assetId"] == "BTCUSD"
    url = str(route.calls.last.request.url)
    assert "startBusinessDate=2024-01-01" in url
    assert "endBusinessDate=2024-01-10" in url
    assert "includeAttributes=true" in url


def test_get_time_series_validations():
    with pytest.raises(ValueError):  # malformed date
        server.get_time_series_data("A", "S", "not-a-date", "2024-01-01")
    with pytest.raises(ValueError):  # end < start
        server.get_time_series_data("A", "S", "2024-02-01", "2024-01-01")
    with pytest.raises(ValueError):  # unbounded / too-large range rejected
        server.get_time_series_data("A", "S", "2020-01-01", "2024-01-01")


def test_get_time_series_rejects_empty_ids():
    # empty ids must error (so a weak LLM gets corrected instead of silent empty data)
    with pytest.raises(ValueError, match="assetId"):
        server.get_time_series_data("", "BITFINEX", "2024-01-01", "2024-01-10")
    with pytest.raises(ValueError, match="dataSourceId"):
        server.get_time_series_data("BTCUSD", "   ", "2024-01-01", "2024-01-10")


def test_parse_text_tool_call_fallback():
    from acme_dwh.mcp.ollama_client import _parse_text_tool_call

    names = {"list_data_sources", "get_time_series_data"}
    text = 'Sure, I will call: {"name": "list_data_sources", "parameters": {"limit": 100, "offset": 0}} next.'
    assert _parse_text_tool_call(text, names) == ("list_data_sources", {"limit": 100, "offset": 0})
    assert _parse_text_tool_call("no tool call here", names) is None
    assert _parse_text_tool_call('{"name": "unknown", "parameters": {}}', names) is None
