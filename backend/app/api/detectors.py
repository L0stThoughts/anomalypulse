"""Detector config API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import ApiResponse, DetectorConfigSet
from app.repositories import detector_repo

router = APIRouter(prefix="/api/v1", tags=["detectors"])


@router.get("/detectors/{metric_name}", response_model=ApiResponse)
async def get_detector_config(metric_name: str) -> ApiResponse:
    """Get detector configuration for a metric."""
    cfg = await detector_repo.get_config(metric_name)
    return ApiResponse(success=True, data=cfg.model_dump())


@router.put("/detectors/{metric_name}", response_model=ApiResponse)
async def update_detector_config(metric_name: str, config_set: DetectorConfigSet) -> ApiResponse:
    """Update detector configuration for a metric."""
    config_set.metric_name = metric_name
    await detector_repo.upsert_config(metric_name, config_set)
    return ApiResponse(success=True, data={"metric_name": metric_name, "updated": True})
