"""
Metrics endpoint handler for Prometheus scraping.
"""

import asyncio
import contextlib
import logging
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from services.metrics import metrics
from services.settings import settings

logger = logging.getLogger(__name__)


async def metrics_endpoint(request: Request) -> Response:
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus format.
    """
    try:
        # Generate and return metrics
        metrics_data: bytes = metrics.get_metrics()
        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4",
        )
    except Exception as e:
        logger.exception("Error generating metrics")
        return Response(
            content=f"Error generating metrics: {e}",
            status_code=500,
            media_type="text/plain",
        )


async def health_check(request: Request) -> JSONResponse:
    """
    Health check endpoint.
    Returns basic health information.
    """
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now(settings.timezone).isoformat(),
            "service": "cukiller-bot",
        }

        return JSONResponse(health_data)
    except Exception as e:
        logger.exception("Health check failed")
        return JSONResponse(
            {
                "status": "unhealthy",
                "timestamp": datetime.now(settings.timezone).isoformat(),
                "error": str(e),
                "service": "cukiller-bot",
            },
            status_code=503,
        )


def setup_metrics_routes(router: APIRouter) -> None:
    """
    Set up metrics and health check routes.
    """
    router.add_api_route("/metrics", metrics_endpoint, methods=["GET"])
    router.add_api_route("/health", health_check, methods=["GET"])
    logger.info("Metrics routes configured: /metrics, /health")


class MetricsUpdater:
    """
    Background task to periodically update metrics.
    """

    def __init__(self, update_interval: int = 30) -> None:
        self.update_interval = update_interval
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Start the metrics updater task."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._update_loop())
        logger.info("Metrics updater started with %ss interval", self.update_interval)

    async def stop(self):
        """Stop the metrics updater task."""
        if not self._running or not self._task:
            return

        self._running = False
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        logger.info("Metrics updater stopped")

    async def _update_loop(self) -> None:
        """Main update loop."""
        while self._running:
            try:
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in metrics update loop")
                await asyncio.sleep(self.update_interval)


# Global metrics updater instance
metrics_updater = MetricsUpdater()
