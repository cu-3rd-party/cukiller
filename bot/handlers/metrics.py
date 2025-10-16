"""
Metrics endpoint handler for Prometheus scraping.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any

from aiohttp import web
from aiohttp.web import Request, Response

from bot.services.metrics import metrics

logger = logging.getLogger(__name__)


async def metrics_endpoint(request: Request) -> Response:
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus format.
    """
    try:
        # Update metrics from database before serving
        await metrics.update_all_metrics()

        # Generate and return metrics
        metrics_data = metrics.get_metrics()
        return Response(
            text=metrics_data,
            content_type="text/plain; version=0.0.4; charset=utf-8",
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return Response(
            text=f"Error generating metrics: {e}",
            status=500,
            content_type="text/plain",
        )


async def health_check(request: Request) -> Response:
    """
    Health check endpoint.
    Returns basic health information.
    """
    try:
        # Update basic metrics to check database connectivity
        await metrics.update_user_metrics()

        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "cukiller-bot",
        }

        return web.json_response(health_data)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return web.json_response(
            {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "service": "cukiller-bot",
            },
            status=503,
        )


def setup_metrics_routes(app: web.Application) -> None:
    """
    Set up metrics and health check routes.
    """
    app.router.add_get("/metrics", metrics_endpoint)
    app.router.add_get("/health", health_check)
    logger.info("Metrics routes configured: /metrics, /health")


class MetricsUpdater:
    """
    Background task to periodically update metrics.
    """

    def __init__(self, update_interval: int = 60):
        self.update_interval = update_interval
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Start the metrics updater task."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._update_loop())
        logger.info(
            f"Metrics updater started with {self.update_interval}s interval"
        )

    async def stop(self):
        """Stop the metrics updater task."""
        if not self._running or not self._task:
            return

        self._running = False
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        logger.info("Metrics updater stopped")

    async def _update_loop(self):
        """Main update loop."""
        while self._running:
            try:
                await metrics.update_all_metrics()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics update loop: {e}")
                await asyncio.sleep(self.update_interval)


# Global metrics updater instance
metrics_updater = MetricsUpdater()
