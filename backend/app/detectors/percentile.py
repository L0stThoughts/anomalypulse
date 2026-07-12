"""Percentile-band anomaly detector."""

from __future__ import annotations

from typing import Any

import numpy as np

from app.detectors.base import Detector
from app.models.schemas import DetectorResult, MetricPoint


class PercentileDetector(Detector):
    name = "percentile"

    def evaluate(
        self,
        point: MetricPoint,
        window: list[float],
        config: dict[str, Any],
    ) -> DetectorResult:
        params = config.get("params", {})
        min_points = params.get("min_points", 30)
        p_lower = params.get("lower", 0.05)
        p_upper = params.get("upper", 0.95)

        if len(window) < min_points:
            return self._warmup_result(min_points, len(window))

        arr = np.array(window)
        lower_bound = float(np.percentile(arr, p_lower * 100))
        upper_bound = float(np.percentile(arr, p_upper * 100))
        median = float(np.median(arr))

        value = point.value
        is_anomaly = value < lower_bound or value > upper_bound

        # Compute normalized score
        band_width = upper_bound - lower_bound
        if band_width < 1e-10:
            score = 0.0
            direction = "stable"
        elif value > upper_bound:
            overshoot = value - upper_bound
            score = min(overshoot / (band_width + 1e-10), 1.0)
            direction = "high"
        elif value < lower_bound:
            undershoot = lower_bound - value
            score = min(undershoot / (band_width + 1e-10), 1.0)
            direction = "low"
        else:
            # Inside band — compute how close to edge
            dist_to_upper = upper_bound - value
            dist_to_lower = value - lower_bound
            min_dist = min(dist_to_upper, dist_to_lower)
            score = max(0.0, 1.0 - (min_dist / (band_width / 2)))
            score *= 0.3  # Scale down in-band scores
            direction = "normal"

        return DetectorResult(
            detector=self.name,
            score=round(score, 4),
            threshold={"lower": round(lower_bound, 4), "upper": round(upper_bound, 4)},
            is_anomaly=is_anomaly,
            warmup=False,
            explanation={
                "lower_bound": round(lower_bound, 4),
                "upper_bound": round(upper_bound, 4),
                "median": round(median, 4),
                "current_value": round(value, 4),
                "direction": direction,
                "p_lower": p_lower,
                "p_upper": p_upper,
            },
        )
