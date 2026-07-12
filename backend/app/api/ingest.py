"""Ingest API endpoints with rate limiting."""

from __future__ import annotations

import time
import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Request, HTTPException

from app.config import config
from app.models.schemas import MetricPoint, MetricPointBatch, ApiResponse
from app.services import ingestion_service

logger = logging.getLogger("anomalypulse.api.ingest")
router = APIRouter(prefix="/api/v1", tags=["ingest"])

# Simple in-memory rate limiting
_rate_counters: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(client_ip: str, limit: int) -> bool:
    """Check if client is within rate limit. Returns True if allowed."""
    now = time.time()
    window = _rate_counters[client_ip]
    # Remove entries older than 1 second
    cutoff = now - 1.0
    _rate_counters[client_ip] = [t for t in window if t > cutoff]
    if len(_rate_counters[client_ip]) >= limit:
        return False
    _rate_counters[client_ip].append(now)
    return True


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/ingest", response_model=ApiResponse)
async def ingest_single(point: MetricPoint, request: Request) -> ApiResponse:
    """Ingest a single metric point."""
    client_ip = _get_client_ip(request)
    if not _check_rate_limit(client_ip, config.rate_limits.ingest_per_sec):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    result = await ingestion_service.ingest_point(point)
    return ApiResponse(success=True, data=result)


@router.post("/ingest/batch", response_model=ApiResponse)
async def ingest_batch(batch: MetricPointBatch, request: Request) -> ApiResponse:
    """Ingest a batch of metric points."""
    client_ip = _get_client_ip(request)
    if not _check_rate_limit(f"{client_ip}_batch", config.rate_limits.batch_per_sec):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    if len(batch.points) > config.rate_limits.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(batch.points)} exceeds maximum {config.rate_limits.max_batch_size}",
        )

    if not batch.points:
        return ApiResponse(success=True, data={"accepted": 0, "queued": 0})

    result = await ingestion_service.ingest_batch(batch)
    return ApiResponse(success=True, data=result)
