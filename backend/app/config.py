"""Application configuration with Pydantic settings."""

from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field


class DetectorDefaults(BaseModel):
    zscore_window: int = 60
    zscore_sigma: float = 3.0
    zscore_min_points: int = 20
    ewma_window: int = 60
    ewma_alpha: float = 0.25
    ewma_k: float = 2.5
    ewma_min_points: int = 20
    iforest_window: int = 120
    iforest_contamination: float = 0.03
    iforest_retrain_every: int = 30
    iforest_min_points: int = 50
    percentile_window: int = 120
    percentile_lower: float = 0.05
    percentile_upper: float = 0.95
    percentile_min_points: int = 30
    ensemble_mode: str = "majority"


class RateLimitConfig(BaseModel):
    ingest_per_sec: int = 50
    batch_per_sec: int = 10
    max_batch_size: int = 1000
    ws_points_per_sec: int = 500


class AppConfig(BaseModel):
    db_path: str = Field(default="anomalypulse.db")
    queue_size: int = Field(default=10000)
    rate_limits: RateLimitConfig = Field(default_factory=RateLimitConfig)
    detector_defaults: DetectorDefaults = Field(default_factory=DetectorDefaults)
    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8080)
    max_active_streams: int = Field(default=1000)
    stream_eviction_seconds: int = Field(default=900)
    default_window_size: int = Field(default=120)
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load config from environment variables with sensible defaults."""
        return cls(
            db_path=os.getenv("AP_DB_PATH", "anomalypulse.db"),
            queue_size=int(os.getenv("AP_QUEUE_SIZE", "10000")),
            server_host=os.getenv("AP_HOST", "0.0.0.0"),
            server_port=int(os.getenv("AP_PORT", "8080")),
            max_active_streams=int(os.getenv("AP_MAX_STREAMS", "1000")),
            stream_eviction_seconds=int(os.getenv("AP_STREAM_EVICTION", "900")),
            rate_limits=RateLimitConfig(
                ingest_per_sec=int(os.getenv("AP_RATE_INGEST", "50")),
                batch_per_sec=int(os.getenv("AP_RATE_BATCH", "10")),
                max_batch_size=int(os.getenv("AP_MAX_BATCH", "1000")),
                ws_points_per_sec=int(os.getenv("AP_RATE_WS", "500")),
            ),
            detector_defaults=DetectorDefaults(
                ensemble_mode=os.getenv("AP_ENSEMBLE_MODE", "majority"),
            ),
        )


# Global singleton
config = AppConfig.from_env()
