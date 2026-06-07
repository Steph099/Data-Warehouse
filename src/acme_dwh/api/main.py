"""FastAPI application — the warehouse consumption layer plus UI-facing
operational endpoints (ingest, analytics, assistant).

Run:
    uvicorn acme_dwh.api.main:app --reload
Interactive docs at http://127.0.0.1:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from acme_dwh.api.routers import analytics, assets, assistant, data, data_sources, ingest
from acme_dwh.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Acme Ltd — Financial Markets Data API",
    version="0.1.0",
    description=(
        "Bi-temporal financial data warehouse. Read queries (assets, data sources, "
        "time series) plus ingestion, Spark analytics, and a grounded LLM assistant."
    ),
)

# Permissive CORS for the local React dev server (it also proxies, so this is a backup).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (assets, data_sources, data, ingest, analytics, assistant):
    app.include_router(module.router, prefix=settings.api_base_path)


@app.get("/health", tags=["meta"], summary="Liveness probe")
def health() -> dict[str, str]:
    return {"status": "ok"}
