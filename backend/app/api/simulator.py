"""Simulator API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.models.schemas import ApiResponse
from app import simulator as sim_engine

router = APIRouter(prefix="/api/v1", tags=["simulator"])


class SimulatorStartRequest(BaseModel):
    scenario: str = "normal"
    rate_per_second: float = 4.0
    metrics: list[str] = Field(default_factory=lambda: [
        "cpu.usage", "memory.usage", "disk.io", "network.bytes", "api.latency"
    ])


@router.post("/simulator/start", response_model=ApiResponse)
async def start_simulator(req: SimulatorStartRequest) -> ApiResponse:
    """Start the metric simulator."""
    await sim_engine.start(
        scenario=req.scenario,
        rate_per_second=req.rate_per_second,
        metrics=req.metrics,
    )
    return ApiResponse(
        success=True,
        data={"running": True, "scenario": req.scenario},
    )


@router.post("/simulator/stop", response_model=ApiResponse)
async def stop_simulator() -> ApiResponse:
    """Stop the metric simulator."""
    await sim_engine.stop()
    return ApiResponse(success=True, data={"running": False})


@router.get("/simulator/status", response_model=ApiResponse)
async def simulator_status() -> ApiResponse:
    """Get simulator status."""
    status = sim_engine.get_status()
    return ApiResponse(success=True, data=status)
