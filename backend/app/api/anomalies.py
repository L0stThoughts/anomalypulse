"""Anomalies API endpoint."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.models.schemas import ApiResponse
from app.repositories import anomaly_repo

router = APIRouter(prefix="/api/v1", tags=["anomalies"])


@router.get("/anomalies", response_model=ApiResponse)
async def get_anomalies(
    metric: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    start: Optional[int] = Query(None, description="Start timestamp (epoch ms)"),
    end: Optional[int] = Query(None, description="End timestamp (epoch ms)"),
    limit: int = Query(100, ge=1, le=10000),
) -> ApiResponse:
    """Get anomaly events with optional filters."""
    results = await anomaly_repo.get_anomalies(
        metric=metric,
        severity=severity,
        start=start,
        end=end,
        limit=limit,
    )
    return ApiResponse(success=True, data=results)
