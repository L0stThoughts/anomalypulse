"""WebSocket connection manager with per-client queues and subscription filtering."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("anomalypulse.streaming.manager")

# Event priority: higher = more important, less likely to be dropped
EVENT_PRIORITY: dict[str, int] = {
    "alert_triggered": 3,
    "anomaly_detected": 2,
    "system_status": 2,
    "simulator_status": 1,
    "metric_point": 0,
}


class ClientConnection:
    """Represents a single WebSocket client with its own outbound queue and subscription."""

    def __init__(self, ws: WebSocket, client_id: str, max_queue: int = 500) -> None:
        self.ws = ws
        self.client_id = client_id
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max_queue)
        self.subscribed_metrics: set[str] = set()  # empty = all
        self.subscribed_events: set[str] = {"metric_point", "anomaly_detected", "alert_triggered"}
        self.active = True
        self._send_task: asyncio.Task | None = None

    def matches(self, event: dict[str, Any]) -> bool:
        """Check if this client's subscription matches the event."""
        event_type = event.get("type", "")
        if event_type not in self.subscribed_events:
            return False

        # If no metric filter, accept all
        if not self.subscribed_metrics:
            return True

        # Extract metric name from payload
        payload = event.get("payload", {})
        metric = payload.get("metric_name") or payload.get("metric", "")
        if metric and metric not in self.subscribed_metrics:
            return False

        return True

    def update_subscription(self, metrics: list[str], events: list[str]) -> None:
        """Update this client's subscription filter."""
        self.subscribed_metrics = set(metrics) if metrics else set()
        self.subscribed_events = set(events) if events else {
            "metric_point", "anomaly_detected", "alert_triggered"
        }

    async def start_sender(self) -> None:
        """Start the background sender task for this client."""
        self._send_task = asyncio.create_task(self._sender_loop())

    async def _sender_loop(self) -> None:
        """Continuously drain the outbound queue and send to WebSocket."""
        while self.active:
            try:
                msg = await asyncio.wait_for(self.queue.get(), timeout=30.0)
                await self.ws.send_json(msg)
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await self.ws.send_json({"type": "ping", "version": 1, "payload": {}})
                except Exception:
                    self.active = False
                    break
            except Exception as e:
                logger.debug(f"Client {self.client_id} send error: {e}")
                self.active = False
                break

    async def stop(self) -> None:
        """Stop the sender and mark inactive."""
        self.active = False
        if self._send_task:
            self._send_task.cancel()
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass


class ConnectionManager:
    """Manages all WebSocket dashboard connections."""

    def __init__(self) -> None:
        self._clients: dict[str, ClientConnection] = {}
        self._counter = 0

    async def connect(self, ws: WebSocket) -> ClientConnection:
        """Accept a new WebSocket connection and register it."""
        await ws.accept()
        self._counter += 1
        client_id = f"client_{self._counter}"
        client = ClientConnection(ws, client_id)
        self._clients[client_id] = client
        await client.start_sender()
        logger.info(f"WebSocket client connected: {client_id} (total: {len(self._clients)})")
        return client

    async def disconnect(self, client: ClientConnection) -> None:
        """Remove a client connection."""
        await client.stop()
        self._clients.pop(client.client_id, None)
        logger.info(f"WebSocket client disconnected: {client.client_id} (total: {len(self._clients)})")

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Broadcast an event to all matching clients."""
        event_type = event.get("type", "")
        priority = EVENT_PRIORITY.get(event_type, 0)
        dead_clients: list[ClientConnection] = []

        for client in self._clients.values():
            if not client.active:
                dead_clients.append(client)
                continue

            if not client.matches(event):
                continue

            try:
                client.queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop low-priority events for slow clients
                if priority <= 1:
                    logger.debug(f"Dropped {event_type} for slow client {client.client_id}")
                else:
                    # For high-priority events, try to make room by dropping oldest low-priority
                    try:
                        # Drain one item to make room
                        client.queue.get_nowait()
                        client.queue.put_nowait(event)
                    except (asyncio.QueueEmpty, asyncio.QueueFull):
                        logger.warning(f"Cannot deliver {event_type} to client {client.client_id}")

        # Clean up dead clients
        for client in dead_clients:
            await self.disconnect(client)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def get_stats(self) -> dict[str, Any]:
        """Get manager statistics."""
        return {
            "total_clients": len(self._clients),
            "clients": [
                {
                    "id": c.client_id,
                    "active": c.active,
                    "queue_size": c.queue.qsize(),
                    "subscribed_metrics": list(c.subscribed_metrics),
                    "subscribed_events": list(c.subscribed_events),
                }
                for c in self._clients.values()
            ],
        }


# Global singleton
manager = ConnectionManager()
