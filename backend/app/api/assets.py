"""
Asset endpoints.

GET  /assets/{asset_id}         — retrieve a single asset
PATCH /assets/{asset_id}/status — mark as flagged / alternative / recommended
"""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Literal

from app.core.db import get_db
from app.models.models import Asset
from app.schemas.schemas import AssetResponse

router = APIRouter(prefix="/assets", tags=["Assets"])

VALID_STATUSES = {"recommended", "alternative", "flagged"}


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return asset


@router.patch("/{asset_id}/status", response_model=AssetResponse)
def update_asset_status(
    asset_id: str,
    new_status: str = Body(..., embed=True, alias="status"),
    db: Session = Depends(get_db),
):
    """Allows editors to manually re-classify an asset."""
    if new_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of: {sorted(VALID_STATUSES)}",
        )
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    asset.status = new_status
    db.commit()
    db.refresh(asset)
    return asset
