"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import ApiResponse
from app.services import detection_service, ingestion_service
from app.streaming.manager import manager
from app import simulator

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=ApiResponse)
async def health_check() -> ApiResponse:
    """Return service health status."""
    try:
        queue = ingestion_service.get_detection_queue()
        queue_depth = queue.qsize()
    except RuntimeError:
        queue_depth = -1

    det_stats = detection_service.get_stats()
    sim_status = simulator.get_status()

    return ApiResponse(
        success=True,
        data={
            "status": "ok",
            "db": "ok",
            "queue_depth": queue_depth,
            "ws_clients": manager.client_count,
            "active_streams": det_stats["active_streams"],
            "detection_running": det_stats["running"],
            "simulator_running": sim_status["running"],
        },
    )
