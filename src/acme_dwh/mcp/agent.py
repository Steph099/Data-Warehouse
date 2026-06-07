"""Web-facing agent: the same tool-calling loop as the CLI assistant, but it calls
the MCP tool functions directly (no stdio subprocess) so it can run inside an HTTP
request. Returns a structured result (answer + tool-call trace) instead of printing.
"""
from __future__ import annotations

import json

from acme_dwh.config import get_settings
from acme_dwh.mcp import server

SYSTEM_PROMPT = (
    "You are a financial-data assistant for Acme Ltd's data warehouse. "
    "Use the tools to read real data. NEVER invent or guess tickers, prices, dates, or numbers; "
    "if a tool errors or returns no records, say so and do not fabricate.\n\n"
    "Call exactly ONE tool per step and WAIT for its result before the next step. "
    "For a price/trend question follow this order:\n"
    "  step 1: list_assets  -> read the asset id (e.g. BTCUSD)\n"
    "  step 2: list_data_sources  -> read the data source id (e.g. BITFINEX)\n"
    "  step 3: get_time_series_data using the EXACT assetId and dataSourceId from steps 1-2 "
    "and a bounded ISO date range (YYYY-MM-DD, half-open end)\n"
    "Do NOT call get_time_series_data until you have a concrete assetId AND dataSourceId; never pass empty ids. "
    "When the data returns, write a short answer using the actual returned numbers."
)
MAX_ROUNDS = 8

# ollama tool schemas mirroring the @mcp.tool functions in server.py
TOOLS = [
    {"type": "function", "function": {
        "name": "list_assets",
        "description": "List financial asset ids (paged, alphabetical). Returns {offset,limit,count,assetIds[]}.",
        "parameters": {"type": "object", "properties": {
            "offset": {"type": "integer"}, "limit": {"type": "integer"}}}}},
    {"type": "function", "function": {
        "name": "get_asset_details",
        "description": "Latest details (identity + attributes) for one asset id.",
        "parameters": {"type": "object", "properties": {"assetId": {"type": "string"}},
                       "required": ["assetId"]}}},
    {"type": "function", "function": {
        "name": "list_data_sources",
        "description": "List data-source ids (paged, alphabetical). Returns {offset,limit,count,dataSourceIds[]}.",
        "parameters": {"type": "object", "properties": {
            "offset": {"type": "integer"}, "limit": {"type": "integer"}}}}},
    {"type": "function", "function": {
        "name": "get_data_source_details",
        "description": "Latest details for one data source, including supported indicator attributes.",
        "parameters": {"type": "object", "properties": {"dataSourceId": {"type": "string"}},
                       "required": ["dataSourceId"]}}},
    {"type": "function", "function": {
        "name": "get_time_series_data",
        "description": "Time-series for an asset+source over a bounded ISO date range [start,end); newest first, latest version per date.",
        "parameters": {"type": "object", "properties": {
            "assetId": {"type": "string"}, "dataSourceId": {"type": "string"},
            "startBusinessDate": {"type": "string"}, "endBusinessDate": {"type": "string"},
            "includeAttributes": {"type": "boolean"}},
            "required": ["assetId", "dataSourceId", "startBusinessDate", "endBusinessDate"]}}},
]

_DISPATCH = {
    "list_assets": server.list_assets,
    "get_asset_details": server.get_asset_details,
    "list_data_sources": server.list_data_sources,
    "get_data_source_details": server.get_data_source_details,
    "get_time_series_data": server.get_time_series_data,
}


def _coerce(args: dict) -> dict:
    # ollama may send numbers/bools as strings; coerce the known typed args
    args = dict(args)
    for key in ("offset", "limit"):
        if key in args and args[key] is not None:
            try:
                args[key] = int(args[key])
            except (TypeError, ValueError):
                pass
    if "includeAttributes" in args and not isinstance(args["includeAttributes"], bool):
        args["includeAttributes"] = str(args["includeAttributes"]).strip().lower() == "true"
    return args


def _parse_text_tool_call(text: str, names: set[str]) -> tuple[str, dict] | None:
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("name") in names:
            args = obj.get("parameters") or obj.get("arguments") or {}
            if isinstance(args, dict):
                return obj["name"], args
    return None


def run_agent(question: str) -> dict:
    """Run the tool-calling loop. Returns {answer, steps, error}."""
    import ollama

    settings = get_settings()
    client = ollama.Client(host=settings.ollama_host)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    steps: list[dict] = []

    for _ in range(MAX_ROUNDS):
        try:
            response = client.chat(
                model=settings.ollama_model, messages=messages, tools=TOOLS,
                options={"temperature": 0},
            )
        except Exception as exc:  # noqa: BLE001 - Ollama unreachable / model missing
            return {"answer": None, "steps": steps, "error": f"Ollama error: {exc}"}

        message = response.message
        messages.append(message)
        calls = [(c.function.name, dict(c.function.arguments or {}))
                 for c in (message.tool_calls or [])]
        if not calls and (message.content or "").strip():
            parsed = _parse_text_tool_call(message.content, set(_DISPATCH))
            if parsed:
                calls = [parsed]
        if not calls:
            return {"answer": message.content or "", "steps": steps, "error": None}

        for name, args in calls:
            fn = _DISPATCH.get(name)
            try:
                if fn is None:
                    raise ValueError(f"unknown tool '{name}'")
                result = fn(**_coerce(args))
                text, ok = json.dumps(result, default=str), True
            except Exception as exc:  # noqa: BLE001
                text, ok = f"ERROR: {exc}", False
            steps.append({"tool": name, "args": args, "ok": ok})
            messages.append({"role": "tool", "content": text, "tool_name": name})

    return {"answer": None, "steps": steps, "error": "reached the tool-call limit"}
