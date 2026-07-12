"""Alert rules and alert events repository."""

from __future__ import annotations

import json
import time
import logging
import fnmatch
from typing import Any

from app.database import get_db
from app.models.schemas import AlertRule, AlertRuleCreate, AlertRuleUpdate, AlertEvent

logger = logging.getLogger("anomalypulse.repo.alert")


# ── Alert Rules CRUD ───────────────────────────────────────────────────────

async def create_rule(rule_id: str, data: AlertRuleCreate) -> AlertRule:
    """Create a new alert rule."""
    db = await get_db()
    now_ms = int(time.time() * 1000)
    await db.execute(
        """INSERT INTO alert_rules
        (id, name, enabled, metric_pattern, rule_type, severity, thresholds_json,
         cooldown_seconds, actions_json, filters_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            rule_id,
            data.name,
            1,
            data.metric_pattern,
            data.rule_type,
            data.severity,
            json.dumps(data.thresholds),
            data.cooldown_seconds,
            json.dumps(data.actions),
            json.dumps(data.filters),
            now_ms,
            now_ms,
        ),
    )
    await db.commit()
    return AlertRule(
        id=rule_id,
        name=data.name,
        enabled=True,
        metric_pattern=data.metric_pattern,
        rule_type=data.rule_type,
        severity=data.severity,
        thresholds=data.thresholds,
        cooldown_seconds=data.cooldown_seconds,
        actions=data.actions,
        filters=data.filters,
        created_at=now_ms,
        updated_at=now_ms,
    )


async def get_rule(rule_id: str) -> AlertRule | None:
    """Get a single alert rule by id."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM alert_rules WHERE id = ?", (rule_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_rule(row)


async def list_rules() -> list[AlertRule]:
    """List all alert rules."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM alert_rules ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return [_row_to_rule(row) for row in rows]


async def update_rule(rule_id: str, data: AlertRuleUpdate) -> AlertRule | None:
    """Update an existing alert rule."""
    existing = await get_rule(rule_id)
    if existing is None:
        return None

    db = await get_db()
    now_ms = int(time.time() * 1000)
    updates: dict[str, Any] = {}

    if data.name is not None:
        updates["name"] = data.name
    if data.enabled is not None:
        updates["enabled"] = 1 if data.enabled else 0
    if data.metric_pattern is not None:
        updates["metric_pattern"] = data.metric_pattern
    if data.rule_type is not None:
        updates["rule_type"] = data.rule_type
    if data.severity is not None:
        updates["severity"] = data.severity
    if data.thresholds is not None:
        updates["thresholds_json"] = json.dumps(data.thresholds)
    if data.cooldown_seconds is not None:
        updates["cooldown_seconds"] = data.cooldown_seconds
    if data.actions is not None:
        updates["actions_json"] = json.dumps(data.actions)
    if data.filters is not None:
        updates["filters_json"] = json.dumps(data.filters)

    updates["updated_at"] = now_ms

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [rule_id]
    await db.execute(f"UPDATE alert_rules SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get_rule(rule_id)


async def delete_rule(rule_id: str) -> bool:
    """Delete an alert rule. Returns True if deleted."""
    db = await get_db()
    cursor = await db.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))
    await db.commit()
    return cursor.rowcount > 0  # type: ignore


async def get_rules_for_metric(metric_name: str) -> list[AlertRule]:
    """Get all enabled rules whose metric_pattern matches the given metric."""
    all_rules = await list_rules()
    matched: list[AlertRule] = []
    for rule in all_rules:
        if not rule.enabled:
            continue
        # Support simple wildcards: cpu.* matches cpu.usage
        pattern = rule.metric_pattern
        if fnmatch.fnmatch(metric_name, pattern):
            matched.append(rule)
        elif pattern == metric_name:
            matched.append(rule)
    return matched


def _row_to_rule(row: Any) -> AlertRule:
    """Convert a database row to AlertRule model."""
    return AlertRule(
        id=row[0],
        name=row[1],
        enabled=bool(row[2]),
        metric_pattern=row[3],
        rule_type=row[4],
        severity=row[5],
        thresholds=json.loads(row[6]),
        cooldown_seconds=row[7],
        actions=json.loads(row[8]),
        filters=json.loads(row[9]),
        created_at=row[10],
        updated_at=row[11],
    )


# ── Alert Events ───────────────────────────────────────────────────────────

async def insert_alert_event(event: AlertEvent) -> None:
    """Persist an alert event."""
    db = await get_db()
    await db.execute(
        """INSERT INTO alert_events
        (id, rule_id, metric, severity, status, message, triggered_at, resolved_at, context_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event.id,
            event.rule_id,
            event.metric,
            event.severity,
            event.status,
            event.message,
            event.triggered_at,
            event.resolved_at,
            json.dumps(event.context),
        ),
    )
    await db.commit()


async def get_alert_events(
    status: str | None = None,
    severity: str | None = None,
    metric: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query alert events with filters."""
    db = await get_db()
    clauses: list[str] = []
    params: list[Any] = []

    if status and status != "all":
        clauses.append("status = ?")
        params.append(status)
    if severity:
        clauses.append("severity = ?")
        params.append(severity)
    if metric:
        clauses.append("metric = ?")
        params.append(metric)

    where = " AND ".join(clauses) if clauses else "1=1"
    params.append(limit)

    cursor = await db.execute(
        f"""SELECT id, rule_id, metric, severity, status, message, triggered_at, resolved_at, context_json
            FROM alert_events WHERE {where} ORDER BY triggered_at DESC LIMIT ?""",
        params,
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": row[0],
            "rule_id": row[1],
            "metric": row[2],
            "severity": row[3],
            "status": row[4],
            "message": row[5],
            "triggered_at": row[6],
            "resolved_at": row[7],
            "context": json.loads(row[8]),
        }
        for row in rows
    ]


async def update_alert_status(alert_id: str, status: str) -> bool:
    """Update the status of an alert event."""
    db = await get_db()
    now_ms = int(time.time() * 1000) if status == "resolved" else None
    if now_ms:
        cursor = await db.execute(
            "UPDATE alert_events SET status = ?, resolved_at = ? WHERE id = ?",
            (status, now_ms, alert_id),
        )
    else:
        cursor = await db.execute(
            "UPDATE alert_events SET status = ? WHERE id = ?",
            (status, alert_id),
        )
    await db.commit()
    return cursor.rowcount > 0  # type: ignore
