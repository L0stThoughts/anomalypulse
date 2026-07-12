"""Base detector protocol and result model."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.schemas import DetectorResult, MetricPoint


class Detector(ABC):
    """Abstract base class for all anomaly detectors."""

    name: str = "base"

    @abstractmethod
    def evaluate(
        self,
        point: MetricPoint,
        window: list[float],
        config: dict[str, Any],
    ) -> DetectorResult:
        """Evaluate a single metric point against the detector.

        Args:
            point: The current metric point.
            window: Recent values for this metric (oldest first).
            config: Detector-specific configuration dict with keys:
                - enabled: bool
                - window_size: int
                - sensitivity: float
                - params: dict of extra params

        Returns:
            DetectorResult with score, threshold, anomaly flag, and explanation.
        """
        ...

    def _warmup_result(self, needed: int, have: int) -> DetectorResult:
        """Return a non-anomalous warmup result."""
        return DetectorResult(
            detector=self.name,
            score=0.0,
            threshold=0.0,
            is_anomaly=False,
            warmup=True,
            explanation={
                "reason": "insufficient_data",
                "needed": needed,
                "have": have,
            },
        )
