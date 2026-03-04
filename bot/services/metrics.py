"""
Prometheus metrics collection for the
"""

import logging
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar, cast

from aiogram import Bot
from prometheus_client import Counter, Histogram, Info, generate_latest

logger = logging.getLogger(__name__)


P = ParamSpec("P")
T = TypeVar("T")


class BotMetrics:
    """Bot metrics collector for Prometheus."""

    def __init__(self) -> None:
        # Bot activity metrics
        self.messages_received = Counter(
            "cukiller_messages_received_total",
            "Total number of incoming updates processed by the bot",
            ["event_type"],
        )
        self.messages_sent = Counter(
            "cukiller_messages_sent_total",
            "Total number of outgoing messages sent by the bot",
            ["method"],
        )
        self.commands_executed = Counter(
            "cukiller_commands_executed_total",
            "Total number of commands executed",
            ["command"],
        )
        self.actions = Counter(
            "cukiller_actions_total",
            "Total number of bot actions executed",
            ["action_type"],
        )

        # Response time metrics
        self.response_time = Histogram(
            "cukiller_response_time_seconds",
            "Response time for bot operations",
            ["operation_type"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # Bot info
        self.bot_info = Info("cukiller_bot_info", "Information about the bot")
        self.bot_info.info({"version": "0.1.0", "name": "cukiller-bot"})

    def increment_message_received(self, event_type: str):
        """Increment the message received counter."""
        self.messages_received.labels(event_type=event_type).inc()
        logger.debug("Incremented message received counter for %s", event_type)

    def increment_message_sent(self, method: str):
        """Increment the message sent counter."""
        self.messages_sent.labels(method=method).inc()
        logger.debug("Incremented message sent counter for %s", method)

    def increment_command_executed(self, command: str):
        """Increment the command executed counter."""
        self.commands_executed.labels(command=command).inc()
        logger.debug("Incremented command executed counter for %s", command)

    def increment_action(self, action_type: str):
        """Increment the action counter."""
        self.actions.labels(action_type=action_type).inc()
        logger.debug("Incremented action counter for %s", action_type)

    def record_response_time(self, operation_type: str, duration: float):
        """Record response time for an operation."""
        self.response_time.labels(operation_type=operation_type).observe(duration)
        logger.debug("Recorded response time for %s: %ss", operation_type, duration)

    @staticmethod
    def get_metrics() -> bytes:
        """Get the current metrics in Prometheus format."""
        return generate_latest()

    def instrument_bot(self, bot: Bot) -> None:
        if getattr(bot, "_metrics_instrumented", False):
            return

        bot._metrics_instrumented = True  # noqa: SLF001

        async def _wrap_send(
            method_name: str,
            original: Callable[P, Awaitable[T]],
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> T:
            self.increment_message_sent(method_name)
            return await original(*args, **kwargs)

        original_send_message = bot.send_message
        original_send_photo = bot.send_photo

        async def send_message_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            wrapped = cast("Callable[P, Awaitable[T]]", original_send_message)
            return await _wrap_send("send_message", wrapped, *args, **kwargs)

        async def send_photo_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            wrapped = cast("Callable[P, Awaitable[T]]", original_send_photo)
            return await _wrap_send("send_photo", wrapped, *args, **kwargs)

        bot.send_message = send_message_wrapper  # type: ignore[method-assign]
        bot.send_photo = send_photo_wrapper  # type: ignore[method-assign]


# Global metrics instance
metrics = BotMetrics()
