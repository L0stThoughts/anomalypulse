"""Alerts API endpoints — rules CRUD and alert events."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ApiResponse, AlertRuleCreate, AlertRuleUpdate
from app.repositories import alert_repo

router = APIRouter(prefix="/api/v1", tags=["alerts"])


@router.get("/alerts", response_model=ApiResponse)
async def get_alerts(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    metric: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=10000),
) -> ApiResponse:
    """List alert events."""
    events = await alert_repo.get_alert_events(
        status=status, severity=severity, metric=metric, limit=limit
    )
    return ApiResponse(success=True, data=events)


@router.get("/alert-rules", response_model=ApiResponse)
async def list_rules() -> ApiResponse:
    """List all alert rules."""
    rules = await alert_repo.list_rules()
    return ApiResponse(success=True, data=[r.model_dump() for r in rules])


@router.post("/alert-rules", response_model=ApiResponse)
async def create_rule(data: AlertRuleCreate) -> ApiResponse:
    """Create a new alert rule."""
    rule_id = f"rule_{uuid.uuid4().hex[:8]}"
    rule = await alert_repo.create_rule(rule_id, data)
    return ApiResponse(success=True, data={"id": rule.id, "created": True})


@router.put("/alert-rules/{rule_id}", response_model=ApiResponse)
async def update_rule(rule_id: str, data: AlertRuleUpdate) -> ApiResponse:
    """Update an existing alert rule."""
    updated = await alert_repo.update_rule(rule_id, data)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return ApiResponse(success=True, data={"id": rule_id, "updated": True})


@router.delete("/alert-rules/{rule_id}", response_model=ApiResponse)
async def delete_rule(rule_id: str) -> ApiResponse:
    """Delete an alert rule."""
    deleted = await alert_repo.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return ApiResponse(success=True, data={"id": rule_id, "deleted": True})
