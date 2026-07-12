"""Detection service — async queue consumer that runs anomaly detection."""

from __future__ import annotations

import asyncio
import time
import uuid
import logging
from collections import OrderedDict
from typing import Any

from app.config import config
from app.models.schemas import MetricPoint, AnomalyEventInternal, DetectorConfigSet
from app.detectors.ensemble import EnsembleDetector
from app.repositories import anomaly_repo, detector_repo

logger = logging.getLogger("anomalypulse.service.detection")


class RollingWindow:
    """Fixed-size rolling window of float values."""

    __slots__ = ("_data", "_max_size")

    def __init__(self, max_size: int = 300) -> None:
        self._data: list[float] = []
        self._max_size = max_size

    def append(self, value: float) -> None:
        self._data.append(value)
        if len(self._data) > self._max_size:
            self._data = self._data[-self._max_size:]

    @property
    def values(self) -> list[float]:
        return self._data

    def __len__(self) -> int:
        return len(self._data)


class LRUWindowCache:
    """LRU cache of rolling windows per metric, bounded by max entries."""

    def __init__(self, max_entries: int = 1000, window_size: int = 300) -> None:
        self._cache: OrderedDict[str, RollingWindow] = OrderedDict()
        self._max_entries = max_entries
        self._window_size = window_size

    def get_or_create(self, metric_name: str) -> RollingWindow:
        if metric_name in self._cache:
            self._cache.move_to_end(metric_name)
            return self._cache[metric_name]
        # Evict oldest if full
        while len(self._cache) >= self._max_entries:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.debug(f"Evicted window cache for {evicted_key}")
        window = RollingWindow(self._window_size)
        self._cache[metric_name] = window
        return window

    @property
    def size(self) -> int:
        return len(self._cache)


# Module-level state
_ensemble = EnsembleDetector()
_window_cache = LRUWindowCache(
    max_entries=config.max_active_streams,
    window_size=300,
)
_running = False
_task: asyncio.Task | None = None

# References set from main.py
_broadcast_fn: Any = None
_alert_eval_fn: Any = None


def set_broadcast_fn(fn: Any) -> None:
    global _broadcast_fn
    _broadcast_fn = fn


def set_alert_eval_fn(fn: Any) -> None:
    global _alert_eval_fn
    _alert_eval_fn = fn


async def start_consumer(queue: asyncio.Queue) -> None:
    """Start the detection consumer as a background task."""
    global _running, _task
    _running = True
    _task = asyncio.create_task(_consume_loop(queue))
    logger.info("Detection consumer started")


async def stop_consumer() -> None:
    """Stop the detection consumer."""
    global _running, _task
    _running = False
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
    logger.info("Detection consumer stopped")


async def _consume_loop(queue: asyncio.Queue) -> None:
    """Main consume loop — dequeue points and process them."""
    while _running:
        try:
            point: MetricPoint = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break

        try:
            await _process_point(point)
        except Exception as e:
            logger.error(f"Detection error for {point.metric_name}: {e}", exc_info=True)


async def _process_point(point: MetricPoint) -> None:
    """Process a single metric point through the detection pipeline."""
    metric = point.metric_name

    # Get/update rolling window
    window = _window_cache.get_or_create(metric)
    window.append(point.value)

    # Load detector config for this metric
    detector_config = await detector_repo.get_config(metric)

    # Run ensemble
    ensemble_result, individual_results = _ensemble.evaluate(
        point, window.values, detector_config
    )

    # Broadcast the metric point event
    if _broadcast_fn:
        await _broadcast_fn({
            "type": "metric_point",
            "version": 1,
            "payload": {
                "metric_name": point.metric_name,
                "timestamp": point.timestamp,
                "value": point.value,
                "tags": point.tags,
            },
        })

    # If warmup, skip anomaly processing
    if ensemble_result.warmup:
        return

    if not ensemble_result.is_anomaly:
        return

    # Build anomaly event
    severity = ensemble_result.explanation.get("severity", "info")
    contributing = [
        {
            "detector": r.detector,
            "score": r.score,
            "is_anomaly": r.is_anomaly,
            "explanation": r.explanation,
        }
        for r in individual_results
        if not r.warmup
    ]

    context = {
        "ensemble_score": ensemble_result.score,
        "ensemble_mode": detector_config.ensemble_mode,
    }
    # Add individual detector explanations to context
    for r in individual_results:
        if not r.warmup:
            context[f"{r.detector}_explanation"] = r.explanation

    anomaly_event = AnomalyEventInternal(
        id=f"anom_{uuid.uuid4().hex[:12]}",
        metric=metric,
        timestamp=point.timestamp,
        value=point.value,
        score=ensemble_result.score,
        detector="ensemble",
        severity=severity,
        is_anomaly=True,
        contributing_detectors=contributing,
        context=context,
        created_at=int(time.time() * 1000),
    )

    # Persist anomaly
    await anomaly_repo.insert_anomaly(anomaly_event)

    # Broadcast anomaly event
    if _broadcast_fn:
        await _broadcast_fn({
            "type": "anomaly_detected",
            "version": 1,
            "payload": {
                "metric": metric,
                "timestamp": point.timestamp,
                "value": point.value,
                "score": ensemble_result.score,
                "severity": severity,
                "detector": "ensemble",
                "context": {
                    "contributing_detectors": [r.detector for r in individual_results if r.is_anomaly and not r.warmup],
                },
            },
        })

    # Evaluate alert rules
    if _alert_eval_fn:
        await _alert_eval_fn(anomaly_event)

    logger.info(f"Anomaly detected: {metric} score={ensemble_result.score:.3f} severity={severity}")


def get_stats() -> dict[str, Any]:
    """Get detection service statistics."""
    return {
        "active_streams": _window_cache.size,
        "running": _running,
    }
