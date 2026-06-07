"""/analytics endpoints — read the Spark output tables and trigger the Spark jobs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from acme_dwh.api.deps import get_analytics_repo
from acme_dwh.api.schemas import JobRunRequest, JobRunResult, PredictionRow, TotalRow
from acme_dwh.api.spark_runner import JOBS, SparkJobError, run_job
from acme_dwh.dal.analytics_repository import AnalyticsRepository

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/totals", response_model=list[TotalRow], summary="Per-year aggregates (Spark job)")
def totals(
    assetId: str = Query(...),
    dataSourceId: str = Query(...),
    repo: AnalyticsRepository = Depends(get_analytics_repo),
) -> list[TotalRow]:
    return repo.totals(assetId, dataSourceId)


@router.get("/predictions", response_model=list[PredictionRow], summary="Regression predictions (Spark ML)")
def predictions(
    assetId: str = Query(...),
    dataSourceId: str = Query(...),
    limit: int = Query(200, ge=1, le=2000),
    repo: AnalyticsRepository = Depends(get_analytics_repo),
) -> list[PredictionRow]:
    return repo.predictions(assetId, dataSourceId, limit)


@router.post(
    "/jobs/{job}",
    response_model=JobRunResult,
    summary="Run a Spark job (aggregation | regression) in the spark container",
)
def run_spark_job(
    body: JobRunRequest,
    job: str = Path(..., description="aggregation | regression"),
) -> JobRunResult:
    """Launch a containerized Spark job and wait for it to finish.

    ``aggregation`` recomputes the per-year ``totals`` for all pairs; ``regression``
    retrains the ML model for the given asset/source and writes ``regression_results``.
    """
    if job not in JOBS:
        raise HTTPException(status_code=404, detail=f"Unknown job {job!r}. Use one of {sorted(JOBS)}.")
    try:
        result = run_job(job, body.assetId, body.dataSourceId)
    except SparkJobError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return JobRunResult(**result)
