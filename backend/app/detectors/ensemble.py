"""Ensemble detector that combines all individual detector results."""

from __future__ import annotations

import math
import logging
from typing import Any

from app.detectors.base import Detector
from app.detectors.zscore import ZScoreDetector
from app.detectors.ewma import EWMADetector
from app.detectors.isolation_forest import IsolationForestDetector
from app.detectors.percentile import PercentileDetector
from app.models.schemas import DetectorResult, DetectorConfigSet, MetricPoint

logger = logging.getLogger("anomalypulse.detector.ensemble")


class EnsembleDetector:
    """Runs all enabled detectors and combines results."""

    def __init__(self) -> None:
        self.zscore = ZScoreDetector()
        self.ewma = EWMADetector()
        self.iforest = IsolationForestDetector()
        self.percentile = PercentileDetector()

    def _get_detector_and_config(self, cfg: DetectorConfigSet) -> list[tuple[Detector, dict[str, Any]]]:
        """Get list of (detector, config_dict) for enabled detectors."""
        pairs: list[tuple[Detector, dict[str, Any]]] = []
        if cfg.zscore.enabled:
            pairs.append((self.zscore, cfg.zscore.model_dump()))
        if cfg.ewma.enabled:
            pairs.append((self.ewma, cfg.ewma.model_dump()))
        if cfg.isolation_forest.enabled:
            pairs.append((self.iforest, cfg.isolation_forest.model_dump()))
        if cfg.percentile.enabled:
            pairs.append((self.percentile, cfg.percentile.model_dump()))
        return pairs

    def evaluate(
        self,
        point: MetricPoint,
        window: list[float],
        config: DetectorConfigSet,
    ) -> tuple[DetectorResult, list[DetectorResult]]:
        """Run all enabled detectors and produce an ensemble result.

        Returns:
            Tuple of (ensemble_result, individual_results)
        """
        pairs = self._get_detector_and_config(config)
        if not pairs:
            return (
                DetectorResult(
                    detector="ensemble",
                    score=0.0,
                    threshold=0.0,
                    is_anomaly=False,
                    explanation={"reason": "no_detectors_enabled"},
                ),
                [],
            )

        results: list[DetectorResult] = []
        for detector, cfg_dict in pairs:
            try:
                result = detector.evaluate(point, window, cfg_dict)
                results.append(result)
            except Exception as e:
                logger.error(f"Detector {detector.name} failed for {point.metric_name}: {e}")
                results.append(DetectorResult(
                    detector=detector.name,
                    score=0.0,
                    threshold=0.0,
                    is_anomaly=False,
                    explanation={"error": str(e)},
                ))

        # Filter out warmup results for voting
        active_results = [r for r in results if not r.warmup]

        if not active_results:
            return (
                DetectorResult(
                    detector="ensemble",
                    score=0.0,
                    threshold=0.0,
                    is_anomaly=False,
                    warmup=True,
                    explanation={"reason": "all_detectors_warming_up"},
                ),
                results,
            )

        # Compute ensemble score (average of active scores)
        avg_score = sum(r.score for r in active_results) / len(active_results)
        max_score = max(r.score for r in active_results)

        # Count votes
        anomaly_votes = sum(1 for r in active_results if r.is_anomaly)
        total_active = len(active_results)

        # Determine anomaly based on ensemble mode
        mode = config.ensemble_mode
        if mode == "majority":
            is_anomaly = anomaly_votes >= math.ceil(total_active / 2)
        elif mode == "any":
            is_anomaly = anomaly_votes > 0
        elif mode == "weighted":
            # Weighted by score — anomaly if weighted average >= 0.5
            is_anomaly = avg_score >= 0.5
        else:
            is_anomaly = anomaly_votes >= math.ceil(total_active / 2)

        # Derive severity
        severity = self._derive_severity(avg_score, max_score, anomaly_votes, total_active, results)

        # Use the higher of avg and max for final score if anomaly
        final_score = max_score if is_anomaly else avg_score

        contributing = [
            {"detector": r.detector, "score": r.score, "is_anomaly": r.is_anomaly}
            for r in active_results
            if r.is_anomaly
        ]

        ensemble_result = DetectorResult(
            detector="ensemble",
            score=round(final_score, 4),
            threshold={"mode": mode, "votes": f"{anomaly_votes}/{total_active}"},
            is_anomaly=is_anomaly,
            warmup=False,
            explanation={
                "mode": mode,
                "avg_score": round(avg_score, 4),
                "max_score": round(max_score, 4),
                "anomaly_votes": anomaly_votes,
                "total_active": total_active,
                "severity": severity,
                "contributing_detectors": [r.detector for r in active_results if r.is_anomaly],
            },
        )

        return ensemble_result, results

    def _derive_severity(
        self,
        avg_score: float,
        max_score: float,
        anomaly_votes: int,
        total_active: int,
        results: list[DetectorResult],
    ) -> str:
        """Derive severity from ensemble results."""
        if max_score >= 0.9 or (anomaly_votes == total_active and avg_score >= 0.7):
            return "critical"
        elif anomaly_votes >= math.ceil(total_active / 2) and avg_score >= 0.4:
            return "warning"
        elif anomaly_votes > 0:
            return "info"
        return "info"

    def reset_metric(self, metric_name: str) -> None:
        """Reset all detector states for a metric."""
        self.ewma.reset_state(metric_name)
        self.iforest.reset_state(metric_name)
