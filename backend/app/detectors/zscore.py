"""Z-Score anomaly detector."""

from __future__ import annotations

import math
from typing import Any

from app.detectors.base import Detector
from app.models.schemas import DetectorResult, MetricPoint


class ZScoreDetector(Detector):
    name = "zscore"

    def evaluate(
        self,
        point: MetricPoint,
        window: list[float],
        config: dict[str, Any],
    ) -> DetectorResult:
        sigma = config.get("sensitivity", 3.0)
        min_points = config.get("params", {}).get("min_points", 20)

        if len(window) < min_points:
            return self._warmup_result(min_points, len(window))

        mean = sum(window) / len(window)
        variance = sum((v - mean) ** 2 for v in window) / len(window)
        stddev = math.sqrt(variance)

        if stddev < 1e-10:
            return DetectorResult(
                detector=self.name,
                score=0.0,
                threshold=sigma,
                is_anomaly=False,
                warmup=False,
                explanation={
                    "mean": round(mean, 6),
                    "stddev": 0.0,
                    "z_score": 0.0,
                    "direction": "stable",
                    "note": "near-zero variance",
                },
            )

        z = (point.value - mean) / stddev
        abs_z = abs(z)
        # Normalize score to 0-1 range: score = abs_z / (sigma * 2), capped at 1.0
        score = min(abs_z / (sigma * 2), 1.0)
        is_anomaly = abs_z >= sigma

        direction = "high" if z > 0 else "low"

        return DetectorResult(
            detector=self.name,
            score=round(score, 4),
            threshold=sigma,
            is_anomaly=is_anomaly,
            warmup=False,
            explanation={
                "mean": round(mean, 4),
                "stddev": round(stddev, 4),
                "z_score": round(z, 4),
                "abs_z": round(abs_z, 4),
                "direction": direction,
            },
        )
