"""Detector configuration repository."""

from __future__ import annotations

import json
import time
import logging

from app.database import get_db
from app.models.schemas import DetectorConfig, DetectorConfigSet

logger = logging.getLogger("anomalypulse.repo.detector")

# Default config returned when no custom config exists
_DEFAULT_CONFIG = DetectorConfigSet(
    ensemble_mode="majority",
    zscore=DetectorConfig(enabled=True, window_size=60, sensitivity=3.0),
    ewma=DetectorConfig(enabled=True, window_size=60, sensitivity=2.5, params={"alpha": 0.25}),
    isolation_forest=DetectorConfig(
        enabled=True, window_size=120, sensitivity=0.65,
        params={"contamination": 0.03, "retrain_every": 30}
    ),
    percentile=DetectorConfig(
        enabled=True, window_size=120, sensitivity=0.95,
        params={"lower": 0.05, "upper": 0.95}
    ),
)


async def get_config(metric_name: str) -> DetectorConfigSet:
    """Get detector config for a metric, returning defaults if none exists."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT ensemble_mode, zscore_json, ewma_json, iforest_json, percentile_json, updated_at FROM detector_configs WHERE metric_name = ?",
        (metric_name,),
    )
    row = await cursor.fetchone()
    if row is None:
        cfg = _DEFAULT_CONFIG.model_copy()
        cfg.metric_name = metric_name
        return cfg

    return DetectorConfigSet(
        metric_name=metric_name,
        ensemble_mode=row[0],
        zscore=DetectorConfig(**json.loads(row[1])) if row[1] else _DEFAULT_CONFIG.zscore,
        ewma=DetectorConfig(**json.loads(row[2])) if row[2] else _DEFAULT_CONFIG.ewma,
        isolation_forest=DetectorConfig(**json.loads(row[3])) if row[3] else _DEFAULT_CONFIG.isolation_forest,
        percentile=DetectorConfig(**json.loads(row[4])) if row[4] else _DEFAULT_CONFIG.percentile,
        updated_at=row[5],
    )


async def upsert_config(metric_name: str, config_set: DetectorConfigSet) -> None:
    """Insert or update detector config for a metric."""
    db = await get_db()
    now_ms = int(time.time() * 1000)
    await db.execute(
        """INSERT INTO detector_configs
        (metric_name, ensemble_mode, zscore_json, ewma_json, iforest_json, percentile_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(metric_name) DO UPDATE SET
            ensemble_mode = excluded.ensemble_mode,
            zscore_json = excluded.zscore_json,
            ewma_json = excluded.ewma_json,
            iforest_json = excluded.iforest_json,
            percentile_json = excluded.percentile_json,
            updated_at = excluded.updated_at""",
        (
            metric_name,
            config_set.ensemble_mode,
            json.dumps(config_set.zscore.model_dump()),
            json.dumps(config_set.ewma.model_dump()),
            json.dumps(config_set.isolation_forest.model_dump()),
            json.dumps(config_set.percentile.model_dump()),
            now_ms,
        ),
    )
    await db.commit()
    logger.info(f"Detector config upserted for {metric_name}")
