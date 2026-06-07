"""/data-sources endpoints — (list ids) and (details / version history)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from acme_dwh.api.deps import get_data_source_repo
from acme_dwh.api.schemas import DataSourceDetail
from acme_dwh.dal.data_source_repository import DataSourceRepository

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


@router.get("", response_model=list[str], summary="List data-source ids (paged, alphabetical)")
def list_data_sources(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    repo: DataSourceRepository = Depends(get_data_source_repo),
) -> list[str]:
    return repo.list_ids(limit=limit, offset=offset)


@router.get(
    "/{data_source_id:path}",
    response_model=None,
    summary="Data-source details (latest version; ?history=true for all versions)",
)
def get_data_source(
    data_source_id: str,
    history: bool = Query(False, description="Return every stored version, newest first."),
    repo: DataSourceRepository = Depends(get_data_source_repo),
):
    if history:
        versions = repo.find_all(data_source_id)
        if not versions:
            raise HTTPException(status_code=404, detail=f"Data source '{data_source_id}' not found")
        return [DataSourceDetail.from_model(s) for s in versions]

    latest = repo.find_latest(data_source_id)
    if latest is None:
        raise HTTPException(status_code=404, detail=f"Data source '{data_source_id}' not found")
    return DataSourceDetail.from_model(latest)
