import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp
from pydantic import BaseModel, Field, ConfigDict


# ---------- MODELS ----------


class PlayerData(BaseModel):
    model_config = ConfigDict(extra="allow")

    rating: float = Field(default=0, ge=0)
    type: Optional[str] = None
    course_number: Optional[int] = Field(default=None, ge=0)
    group_name: Optional[str] = None


class QueuePlayer(BaseModel):
    player_id: int = Field(..., gt=0)
    data: PlayerData
    joined_at: datetime = Field(default_factory=datetime.now)
    rating: float = Field(..., ge=0)

    @classmethod
    def create(
        cls, player_id: int, player_data: Dict[str, Any]
    ) -> "QueuePlayer":
        data_obj = PlayerData(**player_data)
        return cls(
            player_id=player_id,
            data=data_obj,
            rating=data_obj.rating,
        )


class MatchResult(BaseModel):
    killer_id: int
    victim_id: int
    killer_data: PlayerData
    victim_data: PlayerData
    matched_at: datetime = Field(default_factory=datetime.now)
    match_quality: float = Field(..., ge=0, le=1)


# ---------- SERVICE ----------


class MatchmakingService:
    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger
        self.is_running = False
        self.base_url = settings.matchmaking_service_url.rstrip("/")

    async def healthcheck(self):
        data = await self._request("GET", "/ping/")
        assert data is not None
        self.logger.info("Healthcheck completed successfully")

    # -------------------- REST UTILS --------------------

    async def _request(
        self, method: str, path: str, json_data: Optional[dict] = None
    ) -> Optional[dict]:
        """Unified helper to call the Go microservice via REST"""
        url = f"{self.base_url}{path}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, url, json=json_data, timeout=10
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        self.logger.error(
                            f"HTTP {resp.status} {method} {url}: {text}"
                        )
                        return None
                    if "application/json" in resp.headers.get(
                        "Content-Type", ""
                    ):
                        return await resp.json()
                    return None
        except Exception as e:
            self.logger.error(f"Failed {method} {url}: {e}")
            return None

    # -------------------- QUEUE OPS --------------------

    async def add_player_to_queue(
        self, player_id: int, player_data: Dict[str, Any], queue_type: str
    ) -> bool:
        """Add player to Go service queue"""
        if queue_type not in {"killers", "victims"}:
            self.logger.error(f"Invalid queue type: {queue_type}")
            return False

        queue_player = QueuePlayer.create(player_id, player_data)
        data = queue_player.model_dump()

        endpoint = f"/add/{queue_type}/"
        res = await self._request("POST", endpoint, json_data=data)

        if res is not None:
            self.logger.debug(
                f"Added player {player_id} to {queue_type} queue via REST"
            )
            return True
        return False

    async def add_player_to_queues(
        self, player_id: int, player_data: Dict[str, Any]
    ) -> bool:
        """Add player to both queues"""
        added_killer = await self.add_player_to_queue(
            player_id, player_data, "killer"
        )
        added_victim = await self.add_player_to_queue(
            player_id, player_data, "victim"
        )
        return added_killer and added_victim

    async def get_queues_length(self):
        data = await self._request("GET", "/get/queues/len/")
        return data["Killers"], data["Victims"]

    async def get_player_by_id(self, player_id: int):
        self.logger.debug("Getting player by id %d", player_id)
        data = await self._request("GET", f"/get/player/{player_id}")
        return data["QueuedKiller"], data["QueuedVictim"]

    # -------------------- MATCHMAKING LOGIC --------------------

    async def rate_player_pair(
        self,
        killer: QueuePlayer,
        victim: QueuePlayer,
        cur_time: Optional[datetime] = None,
    ) -> float:
        """Rate match quality between two players"""
        cur_time = cur_time or datetime.now()
        rating_diff = abs(killer.rating - victim.rating)
        if rating_diff > self.settings.max_rating_diff:
            return 0.0

        rating_similarity = 1.0 - min(
            rating_diff / self.settings.max_rating_diff, 1.0
        )
        course_bonus = self.settings.course_coefficient * (
            killer.data.course_number == victim.data.course_number
        )
        group_bonus = self.settings.group_coefficient * (
            killer.data.group_name == victim.data.group_name
        )
        type_bonus = self.settings.type_coefficient * (
            killer.data.type == victim.data.type
        )
        time_bonus = self.settings.time_coefficient * (
            (cur_time - killer.joined_at).total_seconds()
            + (cur_time - victim.joined_at).total_seconds()
        )

        quality = (
            rating_similarity
            + course_bonus
            + group_bonus
            + type_bonus
            + time_bonus
        )
        return max(0.0, min(1.0, quality))

    async def find_best_victim_for_killer(
        self, killer: QueuePlayer, victims: List[QueuePlayer]
    ) -> Optional[QueuePlayer]:
        """Find best victim among candidates"""
        best_victim, best_score = None, 0.0

        for victim in victims:
            if victim.player_id == killer.player_id:
                continue
            score = await self.rate_player_pair(killer, victim)
            if score > best_score and score >= self.settings.quality_threshold:
                best_victim, best_score = victim, score

        return best_victim

    async def process_matchmaking(
        self, killers: List[QueuePlayer], victims: List[QueuePlayer]
    ) -> List[Tuple[QueuePlayer, QueuePlayer]]:
        """Form killer-victim pairs"""
        matched = []
        processed = set()

        killers.sort(key=lambda x: x.joined_at)
        for killer in killers:
            if killer.player_id in processed:
                continue
            victim = await self.find_best_victim_for_killer(killer, victims)
            if victim and victim.player_id not in processed:
                matched.append((killer, victim))
                processed.update({killer.player_id, victim.player_id})
                self.logger.info(
                    f"Matched killer {killer.player_id} with victim {victim.player_id}"
                )

        return matched

    # -------------------- CYCLE CONTROL --------------------

    async def run_matchmaking_cycle(self) -> None:
        """Run one matchmaking iteration (mock queues retrieved externally)"""
        try:
            if not self.is_running:
                return

            # In this version, you would GET queues from the Go service if you expose endpoints for that:
            # killers_data = await self._request("GET", "/queue/killers/")
            # victims_data = await self._request("GET", "/queue/victims/")
            # killers = [QueuePlayer(**k) for k in killers_data] if killers_data else []
            # victims = [QueuePlayer(**v) for v in victims_data] if victims_data else []

            # Placeholder since Go side doesn't yet expose GET queues
            killers, victims = [], []

            if not killers or not victims:
                self.logger.debug("No players to match")
                return

            pairs = await self.process_matchmaking(killers, victims)

            for killer, victim in pairs:
                match_result = MatchResult(
                    killer_id=killer.player_id,
                    victim_id=victim.player_id,
                    killer_data=killer.data,
                    victim_data=victim.data,
                    match_quality=await self.rate_player_pair(killer, victim),
                )

                # Notify Go bot endpoint
                await self._request(
                    "POST", "/match/", json_data=match_result.model_dump()
                )

        except Exception as e:
            self.logger.error(f"Error in matchmaking cycle: {e}")

    async def start(self) -> None:
        self.is_running = True
        self.logger.info("Matchmaking service started (REST mode)")

        while self.is_running:
            await self.run_matchmaking_cycle()
            await asyncio.sleep(self.settings.matchmaking_interval)

    async def stop(self) -> None:
        self.is_running = False
        self.logger.info("Matchmaking service stopped")
