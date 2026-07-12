"""Metrics API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.models.schemas import ApiResponse
from app.repositories import metrics_repo, anomaly_repo

router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.get("/metrics", response_model=ApiResponse)
async def list_metrics() -> ApiResponse:
    """List all known metrics with summary statistics."""
    summaries = await metrics_repo.list_metrics_summary()
    return ApiResponse(
        success=True,
        data=[s.model_dump() for s in summaries],
    )


@router.get("/metrics/{metric_name}/latest", response_model=ApiResponse)
async def get_latest(metric_name: str) -> ApiResponse:
    """Get the latest data point and anomaly status for a metric."""
    point = await metrics_repo.get_latest(metric_name)
    if point is None:
        return ApiResponse(success=True, data={"point": None, "latest_anomaly": None})

    # Get latest anomaly for this metric
    anomalies = await anomaly_repo.get_anomalies(metric=metric_name, limit=1)
    latest_anomaly = None
    if anomalies:
        a = anomalies[0]
        latest_anomaly = {"score": a["score"], "severity": a["severity"]}

    return ApiResponse(
        success=True,
        data={"point": point, "latest_anomaly": latest_anomaly},
    )


@router.get("/metrics/{metric_name}/history", response_model=ApiResponse)
async def get_history(
    metric_name: str,
    start: Optional[int] = Query(None, description="Start timestamp (epoch ms)"),
    end: Optional[int] = Query(None, description="End timestamp (epoch ms)"),
    limit: int = Query(1000, ge=1, le=10000),
) -> ApiResponse:
    """Get historical data points for a metric."""
    points = await metrics_repo.get_history(metric_name, start=start, end=end, limit=limit)
    return ApiResponse(
        success=True,
        data={"metric_name": metric_name, "points": points},
    )
