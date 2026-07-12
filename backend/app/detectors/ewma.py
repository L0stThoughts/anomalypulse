"""EWMA (Exponentially Weighted Moving Average) anomaly detector."""

from __future__ import annotations

import math
from typing import Any

from app.detectors.base import Detector
from app.models.schemas import DetectorResult, MetricPoint


class EWMAState:
    """Maintains per-stream EWMA state."""

    __slots__ = ("ewma", "residuals", "initialized")

    def __init__(self) -> None:
        self.ewma: float = 0.0
        self.residuals: list[float] = []
        self.initialized: bool = False


class EWMADetector(Detector):
    name = "ewma"

    def __init__(self) -> None:
        # Per-metric EWMA state
        self._states: dict[str, EWMAState] = {}

    def _get_state(self, metric_name: str) -> EWMAState:
        if metric_name not in self._states:
            self._states[metric_name] = EWMAState()
        return self._states[metric_name]

    def evaluate(
        self,
        point: MetricPoint,
        window: list[float],
        config: dict[str, Any],
    ) -> DetectorResult:
        k = config.get("sensitivity", 2.5)
        alpha = config.get("params", {}).get("alpha", 0.25)
        min_points = config.get("params", {}).get("min_points", 20)
        max_residuals = config.get("window_size", 60)

        if len(window) < min_points:
            return self._warmup_result(min_points, len(window))

        state = self._get_state(point.metric_name)

        if not state.initialized:
            # Initialize EWMA with mean of the window
            state.ewma = sum(window) / len(window)
            # Compute residuals from history
            temp_ewma = window[0]
            for v in window[1:]:
                temp_ewma = alpha * v + (1 - alpha) * temp_ewma
                residual = v - temp_ewma
                state.residuals.append(residual)
            state.initialized = True

        # Update EWMA
        prev_ewma = state.ewma
        state.ewma = alpha * point.value + (1 - alpha) * prev_ewma

        # Compute residual
        residual = point.value - state.ewma

        # Track residuals for variance estimation
        state.residuals.append(residual)
        if len(state.residuals) > max_residuals:
            state.residuals = state.residuals[-max_residuals:]

        # Compute residual standard deviation
        if len(state.residuals) < 5:
            return DetectorResult(
                detector=self.name,
                score=0.0,
                threshold={"k": k},
                is_anomaly=False,
                warmup=True,
                explanation={"reason": "insufficient_residuals", "count": len(state.residuals)},
            )

        r_mean = sum(state.residuals) / len(state.residuals)
        r_var = sum((r - r_mean) ** 2 for r in state.residuals) / len(state.residuals)
        sigma_r = math.sqrt(r_var)

        if sigma_r < 1e-10:
            return DetectorResult(
                detector=self.name,
                score=0.0,
                threshold={"k": k},
                is_anomaly=False,
                warmup=False,
                explanation={
                    "ewma": round(state.ewma, 4),
                    "residual": round(residual, 4),
                    "sigma_residual": 0.0,
                    "note": "near-zero residual variance",
                },
            )

        upper = state.ewma + k * sigma_r
        lower = state.ewma - k * sigma_r
        is_anomaly = point.value > upper or point.value < lower

        # Normalize score
        deviation = abs(residual) / sigma_r
        score = min(deviation / (k * 2), 1.0)

        return DetectorResult(
            detector=self.name,
            score=round(score, 4),
            threshold={"upper": round(upper, 4), "lower": round(lower, 4)},
            is_anomaly=is_anomaly,
            warmup=False,
            explanation={
                "ewma": round(state.ewma, 4),
                "residual": round(residual, 4),
                "sigma_residual": round(sigma_r, 4),
                "upper_limit": round(upper, 4),
                "lower_limit": round(lower, 4),
                "alpha": alpha,
            },
        )

    def reset_state(self, metric_name: str) -> None:
        """Reset EWMA state for a metric."""
        self._states.pop(metric_name, None)
