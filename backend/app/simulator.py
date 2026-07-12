"""Simulator engine — generates synthetic metrics with anomaly injection."""

from __future__ import annotations

import asyncio
import math
import random
import time
import logging
from typing import Any

from app.models.schemas import MetricPoint
from app.services import ingestion_service

logger = logging.getLogger("anomalypulse.simulator")

_task: asyncio.Task | None = None
_running = False
_scenario = "normal"
_rate = 4.0
_metrics: list[str] = []
_points_generated = 0
_start_time = 0.0


# ── Metric generators ─────────────────────────────────────────────────────

class MetricGenerator:
    """Generates realistic metric values with optional anomaly injection."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.tick = 0
        self._base = self._default_base()
        self._noise_scale = self._default_noise()

    def _default_base(self) -> float:
        defaults = {
            "cpu.usage": 45.0,
            "memory.usage": 62.0,
            "disk.io": 150.0,
            "network.bytes": 5000.0,
            "api.latency": 120.0,
        }
        return defaults.get(self.name, 50.0)

    def _default_noise(self) -> float:
        defaults = {
            "cpu.usage": 8.0,
            "memory.usage": 3.0,
            "disk.io": 40.0,
            "network.bytes": 800.0,
            "api.latency": 25.0,
        }
        return defaults.get(self.name, 5.0)

    def generate_normal(self) -> float:
        """Generate a normal metric value with realistic patterns."""
        self.tick += 1
        # Base sinusoidal pattern (simulates daily cycle compressed)
        cycle = math.sin(self.tick * 0.02) * self._noise_scale * 0.5
        # Random walk component
        walk = random.gauss(0, self._noise_scale * 0.3)
        # Occasional micro-spikes (normal operation)
        micro = random.gauss(0, self._noise_scale * 0.1) if random.random() > 0.9 else 0
        value = self._base + cycle + walk + micro
        # Clamp to realistic ranges
        return self._clamp(value)

    def generate_cpu_spike(self) -> float:
        """Generate values with CPU spike anomaly."""
        self.tick += 1
        if random.random() < 0.08:  # 8% chance of spike
            spike = random.uniform(85, 99)
            return self._clamp(spike)
        return self.generate_normal()

    def generate_memory_leak(self) -> float:
        """Generate values simulating gradual memory leak."""
        self.tick += 1
        # Slow upward drift
        drift = self.tick * 0.05
        base = self.generate_normal()
        leaked = base + drift
        if self.name == "memory.usage":
            return min(leaked, 99.5)
        return self._clamp(leaked)

    def generate_latency_surge(self) -> float:
        """Generate values with latency surges."""
        self.tick += 1
        if random.random() < 0.06:
            surge = self._base * random.uniform(3, 8)
            return self._clamp(surge)
        return self.generate_normal()

    def generate_multi_anomaly(self) -> float:
        """Mix of anomaly types."""
        r = random.random()
        if r < 0.04:
            return self.generate_cpu_spike()
        elif r < 0.08:
            return self.generate_latency_surge()
        elif r < 0.12:
            return self.generate_memory_leak()
        return self.generate_normal()

    def _clamp(self, value: float) -> float:
        """Clamp value to realistic ranges per metric type."""
        ranges = {
            "cpu.usage": (0.0, 100.0),
            "memory.usage": (0.0, 100.0),
            "disk.io": (0.0, 10000.0),
            "network.bytes": (0.0, 100000.0),
            "api.latency": (1.0, 30000.0),
        }
        lo, hi = ranges.get(self.name, (0.0, 100000.0))
        return round(max(lo, min(hi, value)), 2)


# ── Simulator engine ───────────────────────────────────────────────────────

_generators: dict[str, MetricGenerator] = {}


def _get_generator(metric_name: str) -> MetricGenerator:
    if metric_name not in _generators:
        _generators[metric_name] = MetricGenerator(metric_name)
    return _generators[metric_name]


def _generate_value(metric_name: str, scenario: str) -> float:
    gen = _get_generator(metric_name)
    if scenario == "cpu_spike":
        if metric_name == "cpu.usage":
            return gen.generate_cpu_spike()
        return gen.generate_normal()
    elif scenario == "memory_leak":
        if metric_name == "memory.usage":
            return gen.generate_memory_leak()
        return gen.generate_normal()
    elif scenario == "latency_surge":
        if metric_name == "api.latency":
            return gen.generate_latency_surge()
        return gen.generate_normal()
    elif scenario == "multi_anomaly":
        return gen.generate_multi_anomaly()
    else:
        return gen.generate_normal()


async def _simulator_loop() -> None:
    """Main simulator loop — generates and ingests synthetic metrics."""
    global _points_generated, _running
    interval = 1.0 / _rate if _rate > 0 else 0.25

    while _running:
        for metric_name in _metrics:
            if not _running:
                break
            value = _generate_value(metric_name, _scenario)
            point = MetricPoint(
                timestamp=int(time.time() * 1000),
                metric_name=metric_name,
                value=value,
                tags={"source": "simulator", "scenario": _scenario},
            )
            try:
                await ingestion_service.ingest_point(point)
                _points_generated += 1
            except Exception as e:
                logger.error(f"Simulator ingest error: {e}")

        await asyncio.sleep(interval)


async def start(
    scenario: str = "normal",
    rate_per_second: float = 4.0,
    metrics: list[str] | None = None,
) -> None:
    """Start the simulator."""
    global _task, _running, _scenario, _rate, _metrics, _points_generated, _start_time, _generators

    if _running:
        await stop()

    _scenario = scenario
    _rate = max(0.1, rate_per_second)
    _metrics = metrics or ["cpu.usage", "memory.usage", "disk.io", "network.bytes", "api.latency"]
    _points_generated = 0
    _start_time = time.time()
    _generators = {}  # Reset generators for fresh scenario
    _running = True
    _task = asyncio.create_task(_simulator_loop())
    logger.info(f"Simulator started: scenario={scenario}, rate={rate_per_second}/s, metrics={_metrics}")


async def stop() -> None:
    """Stop the simulator."""
    global _running, _task
    _running = False
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
    logger.info("Simulator stopped")


def get_status() -> dict[str, Any]:
    """Get simulator status."""
    return {
        "running": _running,
        "scenario": _scenario,
        "rate_per_second": _rate,
        "metrics": _metrics,
        "points_generated": _points_generated,
        "uptime_seconds": round(time.time() - _start_time, 1) if _running else 0,
    }
