"""/data endpoint — time-series range read.

Half-open [startBusinessDate, endBusinessDate), newest date first, one (latest)
version per date or the version current at ``asOf``, tombstones hidden, and overly
large ranges rejected (MAX_DATA_RANGE_DAYS) to keep reads bounded.
"""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from acme_dwh.api.deps import get_timeseries_repo
from acme_dwh.api.schemas import DataPayload, DataRecord, DataResponse
from acme_dwh.config import get_settings
from acme_dwh.dal.timeseries_repository import TimeSeriesRepository

router = APIRouter(prefix="/data", tags=["data"])


@router.get("", response_model=DataResponse, summary="Time-series for an asset + data source")
def get_data(
    asset_id: str = Query(..., alias="assetId"),
    data_source_id: str = Query(..., alias="dataSourceId"),
    start_business_date: date = Query(..., alias="startBusinessDate"),
    end_business_date: date = Query(..., alias="endBusinessDate"),
    include_attributes: bool = Query(False, alias="includeAttributes"),
    as_of: datetime | None = Query(
        None, alias="asOf", description="System-time snapshot; reproduces a past view."
    ),
    repo: TimeSeriesRepository = Depends(get_timeseries_repo),
) -> DataResponse:
    if end_business_date < start_business_date:
        raise HTTPException(status_code=400, detail="endBusinessDate must be >= startBusinessDate")

    max_days = get_settings().max_data_range_days
    if (end_business_date - start_business_date).days > max_days:
        raise HTTPException(
            status_code=400,
            detail=f"Requested range exceeds the maximum of {max_days} days; narrow the interval.",
        )

    records = repo.find_range(
        asset_id, data_source_id, start_business_date, end_business_date, as_of=as_of
    )
    payload = DataPayload(
        asset_id=asset_id,
        data_source_id=data_source_id,
        records=[DataRecord.from_model(r) for r in records],
    )
    attributes = sorted({key for r in records for key in r.values}) if include_attributes else None
    return DataResponse(data=payload, attributes=attributes)
