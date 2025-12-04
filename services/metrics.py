"""
Prometheus metrics collection for the bot.
"""

import logging

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest

from db.models import Game, Player, User

logger = logging.getLogger(__name__)


class BotMetrics:
    """Bot metrics collector for Prometheus."""

    def __init__(self) -> None:
        # User metrics
        self.user_total = Gauge(
            "cukiller_users_total",
            "Total number of users in the database",
            ["status"],
        )
        self.user_registered = Counter(
            "cukiller_users_registered_total",
            "Total number of user registrations",
        )

        # Game metrics
        self.games_total = Gauge("cukiller_games_total", "Total number of games", ["status"])
        self.games_created = Counter("cukiller_games_created_total", "Total number of games created")

        # Player metrics
        self.players_total = Gauge(
            "cukiller_players_total",
            "Total number of players",
            ["game_id", "game_status"],
        )
        self.players_joined = Counter(
            "cukiller_players_joined_total",
            "Total number of player joins",
            ["game_id"],
        )

        # Bot activity metrics
        self.messages_processed = Counter(
            "cukiller_messages_processed_total",
            "Total number of messages processed",
            ["handler_type"],
        )
        self.commands_executed = Counter(
            "cukiller_commands_executed_total",
            "Total number of commands executed",
            ["command"],
        )
        self.admin_actions = Counter(
            "cukiller_admin_actions_total",
            "Total number of admin actions",
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

    async def update_user_metrics(self):
        """Update user-related metrics from the database."""
        try:
            total_users = await User().all().count()
            confirmed_users = await User().filter(status="confirmed").count()
            pending_users = await User().filter(status="pending").count()

            self.user_total.labels(status="total").set(total_users)
            self.user_total.labels(status="confirmed").set(confirmed_users)
            self.user_total.labels(status="pending").set(pending_users)

            logger.debug(
                f"Updated user metrics: total={total_users}, confirmed={confirmed_users}, pending={pending_users}"
            )
        except Exception as e:
            logger.exception(f"Failed to update user metrics: {e}")

    async def update_game_metrics(self):
        """Update game-related metrics from the database."""
        try:
            total_games = await Game().all().count()
            active_games = await Game().filter(end_date=None).count()
            completed_games = await Game().filter(end_date__not=None).count()

            self.games_total.labels(status="total").set(total_games)
            self.games_total.labels(status="active").set(active_games)
            self.games_total.labels(status="completed").set(completed_games)

            logger.debug(
                f"Updated game metrics: total={total_games}, active={active_games}, completed={completed_games}"
            )
        except Exception as e:
            logger.exception(f"Failed to update game metrics: {e}")

    async def update_player_metrics(self):
        """Update player-related metrics from the database."""
        try:
            games = await Game().all()
            for game in games:
                players_count = await Player().filter(game=game.id).count()
                game_status = "active" if game.end_date is None else "completed"

                self.players_total.labels(game_id=str(game.id), game_status=game_status).set(players_count)

            logger.debug(f"Updated player metrics for {len(games)} games")
        except Exception as e:
            logger.exception(f"Failed to update player metrics: {e}")

    async def update_all_metrics(self):
        """Update all metrics from the database."""
        await self.update_user_metrics()
        await self.update_game_metrics()
        await self.update_player_metrics()

    def increment_user_registration(self):
        """Increment the user registration counter."""
        self.user_registered.inc()
        logger.debug("Incremented user registration counter")

    def increment_game_creation(self):
        """Increment the game creation counter."""
        self.games_created.inc()
        logger.debug("Incremented game creation counter")

    def increment_player_join(self, game_id: int):
        """Increment the player join counter for a specific game."""
        self.players_joined.labels(game_id=str(game_id)).inc()
        logger.debug(f"Incremented player join counter for game {game_id}")

    def increment_message_processed(self, handler_type: str):
        """Increment the message processed counter."""
        self.messages_processed.labels(handler_type=handler_type).inc()
        logger.debug(f"Incremented message processed counter for {handler_type}")

    def increment_command_executed(self, command: str):
        """Increment the command executed counter."""
        self.commands_executed.labels(command=command).inc()
        logger.debug(f"Incremented command executed counter for {command}")

    def increment_admin_action(self, action_type: str):
        """Increment the admin action counter."""
        self.admin_actions.labels(action_type=action_type).inc()
        logger.debug(f"Incremented admin action counter for {action_type}")

    def record_response_time(self, operation_type: str, duration: float):
        """Record response time for an operation."""
        self.response_time.labels(operation_type=operation_type).observe(duration)
        logger.debug(f"Recorded response time for {operation_type}: {duration}s")

    @staticmethod
    def get_metrics() -> bytes:
        """Get the current metrics in Prometheus format."""
        return generate_latest()


# Global metrics instance
metrics = BotMetrics()
