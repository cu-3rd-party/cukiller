from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
import asyncio
import json


class PlayerData(BaseModel):
    model_config = ConfigDict(extra="allow")

    rating: float = Field(default=0, ge=0)

    type: Optional[str] = Field(default=None)
    course_number: Optional[int] = Field(default=None, ge=0)
    group_name: Optional[str] = Field(default=None)


class QueuePlayer(BaseModel):
    """Model for players in the matchmaking queue"""

    player_id: int = Field(..., gt=0)
    data: PlayerData
    joined_at: datetime = Field(default_factory=datetime.now)
    rating: float = Field(..., ge=0)

    @classmethod
    def create(
        cls, player_id: int, player_data: Dict[str, Any]
    ) -> "QueuePlayer":
        """Factory method to create a QueuePlayer from raw data"""
        player_data_obj = PlayerData(**player_data)
        return cls(
            player_id=player_id,
            data=player_data_obj,
            rating=player_data_obj.rating,
        )


class MatchResult(BaseModel):
    """Model for match results"""

    killer_id: int = Field(..., gt=0)
    victim_id: int = Field(..., gt=0)
    killer_data: PlayerData
    victim_data: PlayerData
    matched_at: datetime = Field(default_factory=datetime.now)
    match_quality: float = Field(..., ge=0, le=1)


class MatchmakingService:
    def __init__(self, settings, logger):
        self.settings = settings
        self.is_running = False
        self.logger = logger

        self.killers_queue_key = (
            "matchmaking:killers_queue"  # Players without target
        )
        self.victims_queue_key = (
            "matchmaking:victims_queue"  # Players without killer
        )
        self.matches_key = "matchmaking:matches"

    async def add_player_to_queue(
        self, player_id: int, player_data: Dict[str, Any], queue_type: str
    ) -> bool:
        """
        Add player to specific queue (killers or victims)
        :param player_id:
        :param player_data:
        :param queue_type: can be either "killers" or "victims"
        """
        try:
            if queue_type not in ["killers", "victims"]:
                self.logger.error(f"Invalid queue type: {queue_type}")
                return False

            queue_player = QueuePlayer.create(player_id, player_data)
            player_json = queue_player.model_dump_json()

            if queue_type == "killers":
                queue_key = self.killers_queue_key
            else:
                queue_key = self.victims_queue_key

            # Check if player already exists in this queue
            existing_players = await self.get_players_from_queue(queue_key)
            for existing_player in existing_players:
                if existing_player.player_id == player_id:
                    self.logger.debug(
                        f"Player {player_id} is already in the {queue_type} queue"
                    )
                    return False

            result = self.redis.zadd(
                queue_key, {player_json: queue_player.rating}
            )

            self.logger.debug(
                f"Player {player_id} added to {queue_type} queue with rating {queue_player.rating}"
            )
            return bool(result)
        except Exception as e:
            self.logger.error(
                f"Error adding player {player_id} to {queue_type} queue: {e}"
            )
            return False

    async def add_player_to_queues(
        self, player_id: int, player_data: Dict[str, Any]
    ) -> bool:
        """Add player to both killers and victims queues"""
        try:
            queue_player = QueuePlayer.create(player_id, player_data)
            player_json = queue_player.model_dump_json()

            # Add to both queues
            killer_result = self.redis.zadd(
                self.killers_queue_key, {player_json: queue_player.rating}
            )
            victim_result = self.redis.zadd(
                self.victims_queue_key, {player_json: queue_player.rating}
            )

            self.logger.debug(
                f"Player {player_id} added to both killers and victims queues with rating {queue_player.rating}"
            )
            return bool(killer_result and victim_result)
        except Exception as e:
            self.logger.error(
                f"Error adding player {player_id} to queues: {e}"
            )
            return False

    async def remove_player_from_queues(self, player_id: int) -> bool:
        """Remove player from both killers and victims queues"""
        try:
            removed_from_killers = await self.remove_player_from_queue(
                self.killers_queue_key, player_id
            )
            removed_from_victims = await self.remove_player_from_queue(
                self.victims_queue_key, player_id
            )

            return removed_from_killers or removed_from_victims
        except Exception as e:
            self.logger.error(
                f"Error removing player {player_id} from queues: {e}"
            )
            return False

    async def remove_player_from_queue(
        self, queue_key: str, player_id: int
    ) -> bool:
        """
        Remove player from specific queue

        :param queue_key: can be either "matchmaking:killers_queue" or "matchmaking:victims_queue"
        :param player_id: telegram id of the player's user
        """
        try:
            queue_players = await self.get_players_from_queue(queue_key)
            for player in queue_players:
                if player.player_id == player_id:
                    player_json = player.model_dump_json()
                    self.redis.zrem(queue_key, player_json)
                    self.logger.debug(
                        f"Player {player_id} removed from {queue_key}"
                    )
                    return True
            return False
        except Exception as e:
            self.logger.error(
                f"Error removing player {player_id} from {queue_key}: {e}"
            )
            return False

    async def get_unique_players_in_queues(self) -> Tuple[Set[int], Set[int]]:
        killers, victims = await self.get_players_in_queues()
        ret_killers = set()
        for i in killers:
            ret_killers.add(i.player_id)
        ret_victims = set()
        for i in victims:
            ret_victims.add(i.player_id)
        return ret_killers, ret_victims

    async def get_players_in_queues(
        self,
    ) -> Tuple[List[QueuePlayer], List[QueuePlayer]]:
        """Get all players currently in both queues"""
        killers = await self.get_players_from_queue(self.killers_queue_key)
        victims = await self.get_players_from_queue(self.victims_queue_key)
        return killers, victims

    async def get_players_from_queue(
        self, queue_key: str
    ) -> List[QueuePlayer]:
        """
        Get all players from specific queue.
        :param queue_key: can be either "matchmaking:killers_queue" or "matchmaking:victims_queue"
        """
        try:
            queue_members = self.redis.zrange(
                queue_key, 0, -1, withscores=True
            )
            players = []
            for member, score in queue_members:
                try:
                    player_data = json.loads(member)
                    player = QueuePlayer(**player_data)
                    players.append(player)
                except Exception as e:
                    self.logger.warning(
                        f"Invalid player data in {queue_key}: {e}"
                    )
                    continue
            return players
        except Exception as e:
            self.logger.error(f"Error getting players from {queue_key}: {e}")
            return []

    async def rate_player_pair(
        self,
        killer: QueuePlayer,
        victim: QueuePlayer,
        cur_time: datetime | None = None,
    ) -> float:
        """
        Rates compatibility between killer and victim. Returns value between 0 and 1.
        """
        if cur_time is None:
            cur_time = datetime.now()

        rating_diff = abs(killer.rating - victim.rating)
        if rating_diff > self.settings.max_rating_diff:
            return 0.0

        # Чем ближе рейтинги тем лучше
        rating_similarity = 1.0 - min(
            rating_diff / self.settings.max_rating_diff, 1.0
        )

        # Это хорошо, если курс совпадает
        course_bonus = self.settings.course_coefficient * (
            killer.data.course_number == victim.data.course_number
        )
        # Это плохо, если группа совпадает
        group_bonus = self.settings.group_coefficient * (
            killer.data.group_name == victim.data.group_name
        )
        # Это ужасно, если тип обучения не совпадает
        type_bonus = self.settings.type_coefficient * (
            killer.data.type == victim.data.type
        )
        # Это плохо, если люди долго в очереди ждут
        time_bonus = self.settings.time_coefficient * (
            (cur_time - killer.joined_at).total_seconds()
            + (cur_time - victim.joined_at).total_seconds()
        )

        match_quality = (
            rating_similarity
            + course_bonus
            + group_bonus
            + type_bonus
            + time_bonus
        )
        return max(0.0, min(1.0, match_quality))

    async def find_best_victim_for_killer(
        self, killer: QueuePlayer, victims_queue: List[QueuePlayer]
    ) -> Optional[QueuePlayer]:
        """
        Find the best victim for a killer from the victims queue
        Returns None if no satisfactory matches are found.
        """
        try:
            best_victim = None
            best_score = 0.0
            satisfactory_victims = []

            for victim_candidate in victims_queue:
                if victim_candidate.player_id == killer.player_id:
                    continue

                match_score = await self.rate_player_pair(
                    killer, victim_candidate
                )

                if match_score >= self.settings.quality_threshold:
                    satisfactory_victims.append(
                        (victim_candidate, match_score)
                    )

                    if match_score > best_score:
                        best_score = match_score
                        best_victim = victim_candidate

            if satisfactory_victims:
                return best_victim
            else:
                self.logger.debug(
                    f"No satisfactory victims found for killer {killer.player_id}"
                )
                return None

        except Exception as e:
            self.logger.error(
                f"Error finding victim for killer {killer.player_id}: {e}"
            )
            return None

    async def process_matchmaking(
        self,
    ) -> List[Tuple[QueuePlayer, QueuePlayer]]:
        """Process the matchmaking queues and find suitable killer-victim pairs"""
        try:
            killers_queue, victims_queue = await self.get_players_in_queues()

            if not killers_queue or not victims_queue:
                self.logger.info(
                    "Not enough players in both queues for matchmaking"
                )
                return []

            self.logger.info(
                f"Processing matchmaking for {len(killers_queue)} killers and {len(victims_queue)} victims"
            )

            matched_pairs = []
            processed_killers = set()
            processed_victims = set()

            # Sort killers by join time for consistent matching
            killers_queue.sort(key=lambda x: x.joined_at)

            for killer in killers_queue:
                if killer.player_id in processed_killers:
                    continue

                victim = await self.find_best_victim_for_killer(
                    killer, victims_queue
                )

                if (
                    victim
                    and victim.player_id not in processed_victims
                    and victim.player_id != killer.player_id
                ):
                    # Found a match!
                    matched_pairs.append((killer, victim))
                    processed_killers.add(killer.player_id)
                    processed_victims.add(victim.player_id)

                    # Remove matched players from respective queues
                    await self.remove_player_from_queue(
                        self.killers_queue_key, killer.player_id
                    )
                    await self.remove_player_from_queue(
                        self.victims_queue_key, victim.player_id
                    )

                    self.logger.info(
                        f"Matched killer {killer.player_id} with victim {victim.player_id}"
                    )

            return matched_pairs
        except Exception as e:
            self.logger.error(f"Error processing matchmaking: {e}")
            return []

    async def notify_main_process(
        self, matched_pairs: List[Tuple[QueuePlayer, QueuePlayer]]
    ) -> None:
        """Notify main process about matched killer-victim pairs"""
        try:
            for killer, victim in matched_pairs:
                match_result = MatchResult(
                    killer_id=killer.player_id,
                    victim_id=victim.player_id,
                    killer_data=killer.data,
                    victim_data=victim.data,
                    match_quality=await self.rate_player_pair(killer, victim),
                )

                match_dict = match_result.model_dump()

                self.logger.info(
                    f"Match found: killer {killer.player_id} vs victim {victim.player_id} "
                    f"(quality: {match_dict['match_quality']:.2f})"
                )
                requests.post(
                    "http://bot:8000/match",
                    json={
                        "secret_key": self.settings.secret_key,
                        "killer": killer.player_id,
                        "victim": victim.player_id,
                        "quality": match_dict["match_quality"],
                    },
                )

                match_json = match_result.model_dump_json()
                self.redis.lpush(self.matches_key, match_json)

        except Exception as e:
            self.logger.error(f"Error notifying main process: {e}")

    async def restore_queue_state(self) -> None:
        """Restore matchmaking queues state on service startup"""
        try:
            killers_size = self.redis.zcard(self.killers_queue_key)
            victims_size = self.redis.zcard(self.victims_queue_key)

            if killers_size > 0 or victims_size > 0:
                self.logger.info(
                    f"Restored {killers_size} killers and {victims_size} victims after restart"
                )

                killers, victims = await self.get_players_in_queues()

                valid_killers = 0
                for killer in killers:
                    try:
                        QueuePlayer(**killer.model_dump())
                        valid_killers += 1
                    except Exception as e:
                        self.logger.warning(
                            f"Removing invalid killer data from queue: {e}"
                        )
                        await self.remove_player_from_queue(
                            self.killers_queue_key, killer.player_id
                        )

                valid_victims = 0
                for victim in victims:
                    try:
                        QueuePlayer(**victim.model_dump())
                        valid_victims += 1
                    except Exception as e:
                        self.logger.warning(
                            f"Removing invalid victim data from queue: {e}"
                        )
                        await self.remove_player_from_queue(
                            self.victims_queue_key, victim.player_id
                        )

                self.logger.info(
                    f"Validated {valid_killers} killers and {valid_victims} victims"
                )
            else:
                self.logger.info("No players in queues on service startup")
        except Exception as e:
            self.logger.error(f"Error restoring queue state: {e}")

    async def run_matchmaking_cycle(self) -> None:
        """Run one cycle of matchmaking"""
        try:
            if not self.is_running:
                return

            self.logger.debug("Starting matchmaking cycle")

            matched_pairs = await self.process_matchmaking()

            if matched_pairs:
                await self.notify_main_process(matched_pairs)
                self.logger.info(
                    f"Matchmaking cycle completed: {len(matched_pairs)} killer-victim pairs matched"
                )
            else:
                self.logger.debug(
                    "Matchmaking cycle completed: no matches found"
                )

        except Exception as e:
            self.logger.error(f"Error in matchmaking cycle: {e}")

    async def start(self) -> None:
        """Start the matchmaking service"""
        try:
            self.is_running = True
            self.logger.info("Matchmaking service started")

            # Restore previous state
            await self.restore_queue_state()

            # Main service loop
            while self.is_running:
                await self.run_matchmaking_cycle()
                await asyncio.sleep(self.settings.matchmaking_interval)

        except Exception as e:
            self.logger.error(f"Matchmaking service error: {e}")
            self.is_running = False

    async def stop(self) -> None:
        """Stop the matchmaking service"""
        self.is_running = False
        self.logger.info("Matchmaking service stopping...")

    async def get_player_by_id(
        self, player_id: int
    ) -> Optional[Tuple[QueuePlayer, QueuePlayer]]:
        """Get a specific player from both queues by ID"""
        killers, victims = await self.get_players_in_queues()

        killer_player = None
        victim_player = None

        for killer in killers:
            if killer.player_id == player_id:
                killer_player = killer
                break

        for victim in victims:
            if victim.player_id == player_id:
                victim_player = victim
                break

        return killer_player, victim_player

    async def update_player_rating(
        self, player_id: int, new_rating: float
    ) -> bool:
        """Update a player's rating in both queues"""
        try:
            killer_player, victim_player = await self.get_player_by_id(
                player_id
            )

            success = True

            # Update in killers queue if exists
            if killer_player:
                await self.remove_player_from_queue(
                    self.killers_queue_key, player_id
                )
                updated_data = killer_player.data.model_dump()
                updated_data["rating"] = new_rating
                updated_player = QueuePlayer.create(player_id, updated_data)
                player_json = updated_player.model_dump_json()
                result = self.redis.zadd(
                    self.killers_queue_key, {player_json: new_rating}
                )
                success = success and bool(result)

            # Update in victims queue if exists
            if victim_player:
                await self.remove_player_from_queue(
                    self.victims_queue_key, player_id
                )
                updated_data = victim_player.data.model_dump()
                updated_data["rating"] = new_rating
                updated_player = QueuePlayer.create(player_id, updated_data)
                player_json = updated_player.model_dump_json()
                result = self.redis.zadd(
                    self.victims_queue_key, {player_json: new_rating}
                )
                success = success and bool(result)

            return success
        except Exception as e:
            self.logger.error(f"Error updating player {player_id} rating: {e}")
            return False
