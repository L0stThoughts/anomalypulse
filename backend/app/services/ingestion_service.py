"""Ingestion service — normalize, persist, and enqueue metric points."""

from __future__ import annotations

import asyncio
import json
import time
import logging
from typing import Any

from app.models.schemas import MetricPoint, MetricPointBatch
from app.repositories import metrics_repo

logger = logging.getLogger("anomalypulse.service.ingestion")

# Global detection queue — set during app startup
_detection_queue: asyncio.Queue | None = None


def set_detection_queue(q: asyncio.Queue) -> None:
    """Set the detection queue (called during app startup)."""
    global _detection_queue
    _detection_queue = q


def get_detection_queue() -> asyncio.Queue:
    """Get the detection queue."""
    if _detection_queue is None:
        raise RuntimeError("Detection queue not initialized")
    return _detection_queue


def normalize_timestamp(ts: int | None) -> int:
    """Normalize timestamp to UTC epoch milliseconds."""
    if ts is None or ts <= 0:
        return int(time.time() * 1000)
    # If timestamp looks like seconds (< year 2100 in seconds), convert to ms
    if ts < 4102444800:
        return ts * 1000
    return ts


def normalize_tags(tags: dict[str, str] | None) -> dict[str, str]:
    """Normalize tags: sort keys, strip whitespace."""
    if not tags:
        return {}
    return {k.strip().lower(): v.strip() for k, v in sorted(tags.items())}


async def ingest_point(point: MetricPoint) -> dict[str, Any]:
    """Ingest a single metric point: normalize, persist, enqueue."""
    # Normalize
    point.timestamp = normalize_timestamp(point.timestamp)
    point.tags = normalize_tags(point.tags)
    point.metric_name = point.metric_name.strip().lower()

    # Persist
    await metrics_repo.insert_point(point)

    # Enqueue for detection
    queue = get_detection_queue()
    queued = False
    try:
        queue.put_nowait(point)
        queued = True
    except asyncio.QueueFull:
        logger.warning(f"Detection queue full, point for {point.metric_name} dropped from detection")

    return {
        "accepted": 1,
        "queued": 1 if queued else 0,
        "metric_name": point.metric_name,
    }


async def ingest_batch(batch: MetricPointBatch) -> dict[str, Any]:
    """Ingest a batch of metric points."""
    # Normalize all points
    for p in batch.points:
        p.timestamp = normalize_timestamp(p.timestamp)
        p.tags = normalize_tags(p.tags)
        p.metric_name = p.metric_name.strip().lower()

    # Persist all
    count = await metrics_repo.insert_points_batch(batch.points)

    # Enqueue all for detection
    queue = get_detection_queue()
    queued = 0
    for p in batch.points:
        try:
            queue.put_nowait(p)
            queued += 1
        except asyncio.QueueFull:
            logger.warning(f"Detection queue full during batch ingest, {len(batch.points) - queued} points dropped")
            break

    return {
        "accepted": count,
        "queued": queued,
    }
