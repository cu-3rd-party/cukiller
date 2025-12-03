import logging
import sys
from typing import Any, Dict, Optional, Tuple

import aiohttp

from services import settings


# ---------- SERVICE ----------


class MatchmakingService:
    logger = logging.getLogger("bot.matchmaking")
    base_url = settings.matchmaking_service_url.rstrip("/")

    async def healthcheck(self):
        data = await self._request("GET", "/ping/")
        if data is None:
            self.logger.fatal("Failed to ping matchmaking service")
            sys.exit(1)
        self.logger.info("Healthcheck completed successfully")

    # -------------------- REST UTILS --------------------

    async def _request(
        self, method: str, path: str, json_data: Optional[dict] = None
    ) -> Tuple[Optional[int], Optional[dict]]:
        """Unified helper to call the Go microservice via REST"""
        url = f"{self.base_url}{path}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    json=json_data,
                    timeout=10,
                    headers={"secret-key": settings.secret_key},
                ) as resp:
                    resp.raise_for_status()
                    if "application/json" in resp.headers.get("Content-Type", ""):
                        return resp.status, await resp.json()
                    return resp.status, None
        except Exception as e:
            self.logger.error(f"Failed {method} {url}: {e}")
            return None, None

    # -------------------- QUEUE OPS --------------------

    async def add_player_to_queue(self, player_id: int, player_data: Dict[str, Any], queue_type: str) -> bool:
        """Add player to Go service queue"""
        if queue_type not in {"killer", "victim"}:
            self.logger.error(f"Invalid queue type: {queue_type}")
            return False

        await self._request("POST", f"/add/{queue_type}/", json_data=player_data)
        return True

    async def add_player_to_queues(self, player_id: int, player_data: Dict[str, Any]) -> bool:
        """Add player to both queues"""
        added_killer = await self.add_player_to_queue(player_id, player_data, "killer")
        added_victim = await self.add_player_to_queue(player_id, player_data, "victim")
        return added_killer and added_victim

    async def get_queues_length(self):
        _, data = await self._request("GET", "/get/queues/len/")
        return data["Killers"], data["Victims"]

    async def get_player_by_id(self, player_id: int):
        self.logger.debug("Getting player by id %d", player_id)
        _, data = await self._request("GET", f"/get/player/{player_id}")
        return data["QueuedKiller"], data["QueuedVictim"]

    async def reset_queues(self):
        await self._request("POST", "/queues/update/")
