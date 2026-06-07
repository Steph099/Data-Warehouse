"""/ingest endpoint — run the ETL pipeline from the UI."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from acme_dwh.api.schemas import IngestRequest, IngestStatsModel
from acme_dwh.config import get_settings
from acme_dwh.ingestion.load import Ingestor
from acme_dwh.ingestion.providers import build_extractor, resolve_providers

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "",
    response_model=list[IngestStatsModel],
    summary="Ingest symbols from one or more providers",
)
def run_ingest(body: IngestRequest) -> list[IngestStatsModel]:
    """Ingest each symbol from the requested provider(s).

    ``provider`` may be ``bitfinex``, ``nasdaq_data_link``, ``both``, or a
    comma-separated list. Providers run independently: if one fails (e.g. a bad
    key) the others still complete; a 502 is returned only when all of them fail.
    """
    settings = get_settings()
    try:
        provider_names = resolve_providers(body.provider, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    results: list[IngestStatsModel] = []
    errors: list[str] = []
    for name in provider_names:
        try:
            extractor = build_extractor(name, settings)
        except ValueError as exc:
            errors.append(f"{name}: {exc}")
            continue
        try:
            ingestor = Ingestor(extractor)
            for symbol in body.symbols:
                s = ingestor.ingest_symbol(symbol, body.start, body.end)
                results.append(
                    IngestStatsModel(
                        symbol=s.symbol,
                        assetId=s.asset_id,
                        dataSourceId=s.data_source_id,
                        fetched=s.fetched,
                        transformed=s.transformed,
                        stored=s.stored,
                        skipped=s.skipped,
                        failed=s.failed,
                        attributes=s.attributes,
                    )
                )
        except Exception as exc:  # noqa: BLE001 - provider/network failures surface as 502
            errors.append(f"{name}: {exc}")
        finally:
            close = getattr(extractor, "close", None)
            if callable(close):
                close()

    if not results and errors:
        raise HTTPException(status_code=502, detail="Ingestion failed: " + "; ".join(errors))
    return results
