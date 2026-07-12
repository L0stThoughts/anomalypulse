"""WebSocket endpoints for ingest and dashboard streaming."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.schemas import MetricPoint, WSSubscription
from app.services import ingestion_service
from app.streaming.manager import manager

logger = logging.getLogger("anomalypulse.api.websocket")
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/ingest")
async def ws_ingest(ws: WebSocket) -> None:
    """WebSocket endpoint for metric ingestion (producer)."""
    await ws.accept()
    logger.info("WS ingest client connected")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({
                    "type": "error",
                    "payload": {"code": "INVALID_JSON", "message": "Invalid JSON"},
                })
                continue

            msg_type = data.get("type", "")
            payload = data.get("payload", {})

            if msg_type == "metric_point":
                try:
                    point = MetricPoint(**payload)
                    result = await ingestion_service.ingest_point(point)
                    await ws.send_json({
                        "type": "ack",
                        "payload": {
                            "accepted": True,
                            "metric_name": point.metric_name,
                            "timestamp": point.timestamp,
                        },
                    })
                except Exception as e:
                    await ws.send_json({
                        "type": "error",
                        "payload": {
                            "code": "VALIDATION_ERROR",
                            "message": str(e),
                        },
                    })
            else:
                await ws.send_json({
                    "type": "error",
                    "payload": {
                        "code": "UNKNOWN_TYPE",
                        "message": f"Unknown message type: {msg_type}",
                    },
                })

    except WebSocketDisconnect:
        logger.info("WS ingest client disconnected")
    except Exception as e:
        logger.error(f"WS ingest error: {e}")


@router.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket) -> None:
    """WebSocket endpoint for dashboard streaming (consumer)."""
    client = await manager.connect(ws)
    logger.info(f"WS dashboard client connected: {client.client_id}")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")
            payload = data.get("payload", {})

            if msg_type == "subscribe":
                metrics = payload.get("metrics", [])
                events = payload.get("events", [])
                client.update_subscription(metrics, events)
                await ws.send_json({
                    "type": "ack",
                    "payload": {
                        "subscribed_metrics": list(client.subscribed_metrics),
                        "subscribed_events": list(client.subscribed_events),
                    },
                })
            elif msg_type == "ping":
                await ws.send_json({"type": "pong", "version": 1, "payload": {}})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WS dashboard error: {e}")
    finally:
        await manager.disconnect(client)
        logger.info(f"WS dashboard client disconnected: {client.client_id}")
