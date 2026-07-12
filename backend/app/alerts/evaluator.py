"""Alert evaluator — matches anomaly events against rules with cooldown."""

from __future__ import annotations

import time
import uuid
import logging
from typing import Any

from app.models.schemas import AnomalyEventInternal, AlertEvent
from app.repositories import alert_repo

logger = logging.getLogger("anomalypulse.alerts.evaluator")

# Module-level broadcast function reference
_broadcast_fn: Any = None


def set_broadcast_fn(fn: Any) -> None:
    global _broadcast_fn
    _broadcast_fn = fn


class AlertEvaluator:
    """Evaluates anomaly events against alert rules with cooldown tracking."""

    def __init__(self) -> None:
        # rule_id -> last_fired_timestamp_ms
        self._cooldowns: dict[str, int] = {}

    async def evaluate(self, anomaly: AnomalyEventInternal) -> None:
        """Evaluate an anomaly event against all matching rules."""
        rules = await alert_repo.get_rules_for_metric(anomaly.metric)

        if not rules:
            return

        now_ms = int(time.time() * 1000)

        for rule in rules:
            # Check cooldown
            last_fired = self._cooldowns.get(rule.id, 0)
            cooldown_ms = rule.cooldown_seconds * 1000
            if now_ms - last_fired < cooldown_ms:
                logger.debug(f"Rule {rule.id} in cooldown for {anomaly.metric}")
                continue

            # Check thresholds
            if not self._matches_thresholds(anomaly, rule.thresholds, rule.rule_type):
                continue

            # Check severity filter
            severity_order = {"info": 0, "warning": 1, "critical": 2}
            rule_sev = severity_order.get(rule.severity, 0)
            event_sev = severity_order.get(anomaly.severity, 0)
            if event_sev < rule_sev:
                continue

            # Fire alert
            alert_id = f"alert_{uuid.uuid4().hex[:12]}"
            message = f"{rule.name}: {anomaly.metric} anomaly (score={anomaly.score:.2f}, severity={anomaly.severity})"

            alert_event = AlertEvent(
                id=alert_id,
                rule_id=rule.id,
                metric=anomaly.metric,
                severity=anomaly.severity,
                status="open",
                message=message,
                triggered_at=now_ms,
                context={
                    "anomaly_id": anomaly.id,
                    "anomaly_score": anomaly.score,
                    "value": anomaly.value,
                },
            )

            # Persist
            await alert_repo.insert_alert_event(alert_event)

            # Update cooldown
            self._cooldowns[rule.id] = now_ms

            # Broadcast
            if _broadcast_fn:
                await _broadcast_fn({
                    "type": "alert_triggered",
                    "version": 1,
                    "payload": {
                        "id": alert_id,
                        "metric": anomaly.metric,
                        "severity": anomaly.severity,
                        "message": message,
                        "triggered_at": now_ms,
                        "rule_id": rule.id,
                    },
                })

            logger.info(f"Alert triggered: {alert_id} for rule {rule.id} on {anomaly.metric}")

    def _matches_thresholds(
        self,
        anomaly: AnomalyEventInternal,
        thresholds: dict[str, float],
        rule_type: str,
    ) -> bool:
        """Check if the anomaly matches the rule's thresholds."""
        if rule_type == "anomaly_score":
            score_gte = thresholds.get("score_gte", 0.0)
            return anomaly.score >= score_gte

        elif rule_type == "threshold":
            value_gte = thresholds.get("value_gte")
            value_lte = thresholds.get("value_lte")
            if value_gte is not None and anomaly.value < value_gte:
                return False
            if value_lte is not None and anomaly.value > value_lte:
                return False
            return True

        elif rule_type == "anomaly_burst":
            # For MVP, treat as anomaly_score
            score_gte = thresholds.get("score_gte", 0.5)
            return anomaly.score >= score_gte

        elif rule_type == "sustained_drift":
            score_gte = thresholds.get("score_gte", 0.4)
            return anomaly.score >= score_gte

        # Default: any anomaly matches
        return True

    def clear_cooldowns(self) -> None:
        """Clear all cooldown state."""
        self._cooldowns.clear()


# Global evaluator instance
evaluator = AlertEvaluator()
