"""Pydantic models for the entire AnomalyPulse domain."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Metric Models ──────────────────────────────────────────────────────────

class MetricPoint(BaseModel):
    timestamp: int  # epoch milliseconds UTC
    metric_name: str
    value: float
    tags: dict[str, str] = Field(default_factory=dict)


class MetricPointBatch(BaseModel):
    points: list[MetricPoint]


class MetricSummary(BaseModel):
    name: str
    last_value: float
    mean: float
    stddev: float
    min_value: float = 0.0
    max_value: float = 0.0
    point_count: int = 0
    anomaly_count: int = 0
    last_timestamp: int = 0


# ── Detector Models ────────────────────────────────────────────────────────

class DetectorResult(BaseModel):
    detector: str
    score: float  # 0.0 to 1.0 normalized
    threshold: float | dict[str, float] = 0.0
    is_anomaly: bool
    warmup: bool = False
    explanation: dict[str, Any] = Field(default_factory=dict)


class DetectorConfig(BaseModel):
    enabled: bool = True
    window_size: int = 60
    sensitivity: float = 3.0
    params: dict[str, Any] = Field(default_factory=dict)


class DetectorConfigSet(BaseModel):
    metric_name: str = ""
    ensemble_mode: str = "majority"
    zscore: DetectorConfig = Field(default_factory=lambda: DetectorConfig(
        window_size=60, sensitivity=3.0
    ))
    ewma: DetectorConfig = Field(default_factory=lambda: DetectorConfig(
        window_size=60, sensitivity=2.5, params={"alpha": 0.25}
    ))
    isolation_forest: DetectorConfig = Field(default_factory=lambda: DetectorConfig(
        window_size=120, sensitivity=0.65, params={"contamination": 0.03, "retrain_every": 30}
    ))
    percentile: DetectorConfig = Field(default_factory=lambda: DetectorConfig(
        window_size=120, sensitivity=0.95, params={"lower": 0.05, "upper": 0.95}
    ))
    updated_at: int = 0


# ── Anomaly Models ─────────────────────────────────────────────────────────

class AnomalyEvent(BaseModel):
    metric: str
    timestamp: int
    score: float
    detector: str
    severity: str  # info | warning | critical
    context: dict[str, Any] = Field(default_factory=dict)


class AnomalyEventInternal(BaseModel):
    id: str
    metric: str
    timestamp: int
    value: float
    score: float
    detector: str
    severity: str
    is_anomaly: bool
    contributing_detectors: list[dict[str, Any]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: int = 0


# ── Alert Models ───────────────────────────────────────────────────────────

class AlertRule(BaseModel):
    id: str = ""
    name: str = ""
    enabled: bool = True
    metric_pattern: str = ""
    rule_type: str = "anomaly_score"
    severity: str = "warning"
    thresholds: dict[str, float] = Field(default_factory=dict)
    cooldown_seconds: int = 300
    actions: list[str] = Field(default_factory=lambda: ["dashboard"])
    filters: dict[str, str] = Field(default_factory=dict)
    created_at: int = 0
    updated_at: int = 0


class AlertRuleCreate(BaseModel):
    name: str
    metric_pattern: str
    rule_type: str = "anomaly_score"
    severity: str = "warning"
    thresholds: dict[str, float] = Field(default_factory=dict)
    cooldown_seconds: int = 300
    actions: list[str] = Field(default_factory=lambda: ["dashboard"])
    filters: dict[str, str] = Field(default_factory=dict)


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    metric_pattern: Optional[str] = None
    rule_type: Optional[str] = None
    severity: Optional[str] = None
    thresholds: Optional[dict[str, float]] = None
    cooldown_seconds: Optional[int] = None
    actions: Optional[list[str]] = None
    filters: Optional[dict[str, str]] = None


class AlertEvent(BaseModel):
    id: str
    rule_id: str
    metric: str
    severity: str
    status: str = "open"
    message: str = ""
    triggered_at: int = 0
    resolved_at: Optional[int] = None
    context: dict[str, Any] = Field(default_factory=dict)


# ── Response Envelopes ─────────────────────────────────────────────────────

class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiResponse(BaseModel):
    success: bool = True
    data: Any = None
    error: Optional[ApiError] = None
    meta: dict[str, Any] = Field(default_factory=dict)


# ── WebSocket Message Types ────────────────────────────────────────────────

class WSMessage(BaseModel):
    type: str  # metric_point | anomaly_detected | alert_triggered | ack | error | subscribe | system_status | simulator_status
    version: int = 1
    payload: dict[str, Any] = Field(default_factory=dict)


class WSSubscription(BaseModel):
    metrics: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=lambda: [
        "metric_point", "anomaly_detected", "alert_triggered"
    ])
