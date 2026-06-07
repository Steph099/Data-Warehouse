"""Local-LLM (Ollama) assistant grounded in the warehouse via the MCP server.

Launches the MCP server over stdio, exposes its tools to a local Ollama model, and
runs a multi-step tool-calling loop so the model can chain calls
(list -> details -> time series -> explain) to answer a question.

Prerequisites: Cassandra up + data ingested; the REST API running
(uvicorn acme_dwh.api.main:app); Ollama serving a tool-capable model (ollama pull llama3.2).
Run: acme-assistant "What crypto assets do we have, and how did BTCUSD move recently?"
"""
from __future__ import annotations

import asyncio
import json
import sys

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from acme_dwh.config import get_settings

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


def _to_ollama_tools(mcp_tools) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": (tool.description or "").strip(),
                "parameters": tool.inputSchema,
            },
        }
        for tool in mcp_tools
    ]


def _parse_text_tool_call(text: str, tool_names: set[str]) -> tuple[str, dict] | None:
    """Fallback for small models that emit a tool call as JSON text instead of a
    structured call. Scans for the first ``{"name": <tool>, "parameters"/"arguments": {...}}``."""
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("name") in tool_names:
            args = obj.get("parameters") or obj.get("arguments") or {}
            if isinstance(args, dict):
                return obj["name"], args
    return None


async def answer(question: str) -> None:
    settings = get_settings()
    server = StdioServerParameters(command=sys.executable, args=["-m", "acme_dwh.mcp.server"])

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            ollama_tools = _to_ollama_tools(tools)
            print(f"Connected to MCP server; tools: {', '.join(t.name for t in tools)}\n")

            client = ollama.Client(host=settings.ollama_host)
            tool_names = {t.name for t in tools}
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ]

            for _ in range(MAX_ROUNDS):
                response = client.chat(
                    model=settings.ollama_model,
                    messages=messages,
                    tools=ollama_tools,
                    options={"temperature": 0},
                )
                message = response.message
                messages.append(message)

                calls = [
                    (c.function.name, dict(c.function.arguments or {}))
                    for c in (message.tool_calls or [])
                ]
                if not calls and (message.content or "").strip():
                    parsed = _parse_text_tool_call(message.content, tool_names)
                    if parsed:
                        calls = [parsed]

                if not calls:
                    print("=== Assistant ===\n" + (message.content or "(no answer)"))
                    return

                for name, args in calls:
                    print(f"[tool] {name}({json.dumps(args, default=str)})")
                    try:
                        result = await session.call_tool(name, args)
                        text = "".join(p.text for p in result.content if getattr(p, "text", None))
                        if result.isError:
                            text = f"ERROR: {text}"
                    except Exception as exc:  # noqa: BLE001
                        text = f"ERROR calling {name}: {exc}"
                    messages.append({"role": "tool", "content": text, "tool_name": name})

            print("=== Assistant: reached the tool-call limit without a final answer. ===")


def main() -> None:
    question = " ".join(sys.argv[1:]).strip() or (
        "What assets do we have, and how did BTCUSD trend over the last two weeks of data?"
    )
    asyncio.run(answer(question))


if __name__ == "__main__":
    main()
