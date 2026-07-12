"""Isolation Forest anomaly detector using scikit-learn."""

from __future__ import annotations

import math
import logging
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest

from app.detectors.base import Detector
from app.models.schemas import DetectorResult, MetricPoint

logger = logging.getLogger("anomalypulse.detector.iforest")


class IForestState:
    """Per-metric Isolation Forest state."""

    __slots__ = ("model", "feature_buffer", "points_since_train", "trained")

    def __init__(self) -> None:
        self.model: IsolationForest | None = None
        self.feature_buffer: list[list[float]] = []
        self.points_since_train: int = 0
        self.trained: bool = False


class IsolationForestDetector(Detector):
    name = "isolation_forest"

    def __init__(self) -> None:
        self._states: dict[str, IForestState] = {}

    def _get_state(self, metric_name: str) -> IForestState:
        if metric_name not in self._states:
            self._states[metric_name] = IForestState()
        return self._states[metric_name]

    def _build_feature_vector(
        self, value: float, window: list[float]
    ) -> list[float]:
        """Build a 6-element feature vector: [value, mean, stddev, delta, zscore_proxy, ewma_residual]."""
        if len(window) < 2:
            return [value, value, 0.0, 0.0, 0.0, 0.0]

        mean = sum(window) / len(window)
        variance = sum((v - mean) ** 2 for v in window) / len(window)
        stddev = math.sqrt(variance)
        delta = value - window[-1]

        # Z-score proxy
        zscore_proxy = (value - mean) / stddev if stddev > 1e-10 else 0.0

        # Simple EWMA residual
        alpha = 0.25
        ewma = window[0]
        for v in window[1:]:
            ewma = alpha * v + (1 - alpha) * ewma
        ewma_residual = value - ewma

        return [value, mean, stddev, delta, zscore_proxy, ewma_residual]

    def evaluate(
        self,
        point: MetricPoint,
        window: list[float],
        config: dict[str, Any],
    ) -> DetectorResult:
        params = config.get("params", {})
        min_points = params.get("min_points", 50)
        contamination = params.get("contamination", 0.03)
        retrain_every = params.get("retrain_every", 30)
        sensitivity = config.get("sensitivity", 0.65)

        state = self._get_state(point.metric_name)

        # Build current feature vector
        fv = self._build_feature_vector(point.value, window)

        # Add to buffer
        state.feature_buffer.append(fv)
        max_buffer = config.get("window_size", 120) * 2
        if len(state.feature_buffer) > max_buffer:
            state.feature_buffer = state.feature_buffer[-max_buffer:]

        state.points_since_train += 1

        # Check if we have enough data
        if len(state.feature_buffer) < min_points:
            return self._warmup_result(min_points, len(state.feature_buffer))

        # Train or retrain
        if not state.trained or state.points_since_train >= retrain_every:
            try:
                X = np.array(state.feature_buffer)
                state.model = IsolationForest(
                    contamination=contamination,
                    n_estimators=100,
                    random_state=42,
                    n_jobs=1,
                )
                state.model.fit(X)
                state.trained = True
                state.points_since_train = 0
                logger.debug(f"IForest retrained for {point.metric_name} with {len(X)} samples")
            except Exception as e:
                logger.warning(f"IForest training failed for {point.metric_name}: {e}")
                return DetectorResult(
                    detector=self.name,
                    score=0.0,
                    threshold=sensitivity,
                    is_anomaly=False,
                    warmup=True,
                    explanation={"error": str(e)},
                )

        if state.model is None:
            return self._warmup_result(min_points, len(state.feature_buffer))

        # Score the current point
        fv_arr = np.array([fv])
        raw_score = state.model.decision_function(fv_arr)[0]
        prediction = state.model.predict(fv_arr)[0]

        # Normalize: decision_function returns negative for anomalies
        # Typical range is roughly [-0.5, 0.5]; we map to [0, 1]
        normalized = max(0.0, min(1.0, 0.5 - raw_score))

        is_anomaly = prediction == -1 and normalized >= sensitivity

        return DetectorResult(
            detector=self.name,
            score=round(normalized, 4),
            threshold=sensitivity,
            is_anomaly=is_anomaly,
            warmup=False,
            explanation={
                "raw_score": round(float(raw_score), 4),
                "normalized_score": round(normalized, 4),
                "prediction": int(prediction),
                "contamination": contamination,
                "buffer_size": len(state.feature_buffer),
                "retrained_at_count": state.points_since_train,
                "feature_vector": [round(f, 4) for f in fv],
            },
        )

    def reset_state(self, metric_name: str) -> None:
        """Reset state for a metric."""
        self._states.pop(metric_name, None)
