"""FastAPI application — entry point for AnomalyPulse backend."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.database import init_schema, close_db
from app.services import ingestion_service, detection_service
from app.streaming.manager import manager
from app.alerts.evaluator import evaluator, set_broadcast_fn as alert_set_broadcast
from app.api import ingest, metrics, anomalies, alerts, detectors, simulator, health, websocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("anomalypulse.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # ── Startup ──
    logger.info("AnomalyPulse starting up...")

    # 1. Initialize database schema
    await init_schema()

    # 2. Create bounded detection queue
    detection_queue = asyncio.Queue(maxsize=config.queue_size)
    ingestion_service.set_detection_queue(detection_queue)

    # 3. Wire up broadcast function
    async def broadcast(event: dict) -> None:
        await manager.broadcast(event)

    detection_service.set_broadcast_fn(broadcast)
    alert_set_broadcast(broadcast)

    # 4. Wire up alert evaluator
    detection_service.set_alert_eval_fn(evaluator.evaluate)

    # 5. Start detection consumer
    await detection_service.start_consumer(detection_queue)

    logger.info(f"AnomalyPulse ready on {config.server_host}:{config.server_port}")

    yield

    # ── Shutdown ──
    logger.info("AnomalyPulse shutting down...")
    from app import simulator as sim
    await sim.stop()
    await detection_service.stop_consumer()
    await close_db()
    logger.info("AnomalyPulse shut down complete")


app = FastAPI(
    title="AnomalyPulse",
    description="Real-Time Anomaly Detection Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(ingest.router)
app.include_router(metrics.router)
app.include_router(anomalies.router)
app.include_router(alerts.router)
app.include_router(detectors.router)
app.include_router(simulator.router)
app.include_router(health.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    return {
        "name": "AnomalyPulse",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
