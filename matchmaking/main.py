import asyncio
import logging

from services.matchmaking import MatchmakingService
from settings import get_settings, get_redis_client

logger = logging.getLogger(__name__)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d #%(levelname)-4s [%(asctime)s] - %(name)s - %(message)s",
    )

    settings = get_settings()
    redis = get_redis_client()

    # Initialize matchmaking service
    matchmaking_service = MatchmakingService(redis, settings, logger)

    try:
        # Start the matchmaking service
        await matchmaking_service.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Matchmaking service stopped")
    finally:
        await matchmaking_service.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Matchmaking service stopped")