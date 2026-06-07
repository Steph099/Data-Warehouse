"""/assets endpoints — (list ids) and (details / version history)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from acme_dwh.api.deps import get_asset_repo
from acme_dwh.api.schemas import AssetDetail
from acme_dwh.dal.asset_repository import AssetRepository

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[str], summary="list asset ids (paged, alphabetical)")
def list_assets(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    repo: AssetRepository = Depends(get_asset_repo),
) -> list[str]:
    return repo.list_ids(limit=limit, offset=offset)


@router.get(
    "/{asset_id:path}",
    response_model=None,
    summary="Asset details (latest version; ?history=true for all versions)",
)
def get_asset(
    asset_id: str,
    history: bool = Query(False, description="Return every stored version, newest first."),
    repo: AssetRepository = Depends(get_asset_repo),
):
    if history:
        versions = repo.find_all(asset_id)
        if not versions:
            raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found")
        return [AssetDetail.from_model(a) for a in versions]

    latest = repo.find_latest(asset_id)
    if latest is None:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found")
    return AssetDetail.from_model(latest)
