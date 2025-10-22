from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
import json
import requests


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

    player1_id: int = Field(..., gt=0)
    player2_id: int = Field(..., gt=0)
    player1_data: PlayerData
    player2_data: PlayerData
    matched_at: datetime = Field(default_factory=datetime.now)
    match_quality: float = Field(..., ge=0, le=1)


class MatchmakingService:
    def __init__(self, redis_client, settings, logger):
        self.redis = redis_client
        self.settings = settings
        self.is_running = False
        self.logger = logger

        # Redis keys
        self.queue_key = "matchmaking:queue"
        self.processing_key = "matchmaking:processing"
        self.matches_key = "matchmaking:matches"

    async def add_player_to_queue(
        self, player_id: int, player_data: Dict[str, Any]
    ) -> bool:
        """Add player to matchmaking queue"""
        try:
            existing_players = await self.get_players_in_queue()
            for existing_player in existing_players:
                if existing_player.player_id == player_id:
                    self.logger.debug(
                        f"Player {player_id} is already in the matchmaking queue"
                    )
                    return False

            queue_player = QueuePlayer.create(player_id, player_data)

            player_json = queue_player.model_dump_json()

            result = self.redis.zadd(
                self.queue_key, {player_json: queue_player.rating}
            )

            self.logger.debug(
                f"Player {player_id} added to matchmaking queue with rating {queue_player.rating}"
            )
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error adding player {player_id} to queue: {e}")
            return False

    async def remove_player_from_queue(self, player_id: int) -> bool:
        """Remove player from matchmaking queue"""
        try:
            queue_players = await self.get_players_in_queue()
            for player in queue_players:
                if player.player_id == player_id:
                    player_json = player.model_dump_json()
                    self.redis.zrem(self.queue_key, player_json)
                    self.logger.info(
                        f"Player {player_id} removed from matchmaking queue"
                    )
                    return True
            return False
        except Exception as e:
            self.logger.error(
                f"Error removing player {player_id} from queue: {e}"
            )
            return False

    async def get_players_in_queue(self) -> List[QueuePlayer]:
        """Get all players currently in matchmaking queue"""
        try:
            queue_members = self.redis.zrange(
                self.queue_key, 0, -1, withscores=True
            )
            players = []
            for member, score in queue_members:
                try:
                    player_data = json.loads(member)
                    player = QueuePlayer(**player_data)
                    players.append(player)
                except Exception as e:
                    self.logger.warning(f"Invalid player data in queue: {e}")
                    continue
            return players
        except Exception as e:
            self.logger.error(f"Error getting players from queue: {e}")
            return []

    async def rate_player_pair(
        self,
        player1: QueuePlayer,
        player2: QueuePlayer,
        cur_time: datetime | None = None,
    ) -> float:
        """
        Rates compatibility between two players. Returns value between 0 and 1.
        """
        if cur_time is None:
            cur_time = datetime.now()

        rating_diff = abs(player1.rating - player2.rating)
        if rating_diff > self.settings.max_rating_diff:
            return 0.0

        # Чем ближе рейтинги тем лучше
        rating_similarity = 1.0 - min(
            rating_diff / self.settings.max_rating_diff, 1.0
        )

        # Это хорошо, если курс совпадает
        course_bonus = self.settings.course_coefficient * (
            player1.data.course_number == player2.data.course_number
        )
        # Это плохо, если группа совпадает
        group_bonus = self.settings.group_coefficient * (
            player1.data.group_name == player2.data.group_name
        )
        # Это ужасно, если тип обучения не совпадает
        type_bonus = self.settings.type_coefficient * (
            player1.data.type == player2.data.type
        )
        # Это плохо, если люди долго в очереди ждут
        time_bonus = self.settings.time_coefficient * (
            (cur_time - player1.joined_at).total_seconds()
            + (cur_time - player2.joined_at).total_seconds()
        )

        match_quality = (
            rating_similarity
            + course_bonus
            + group_bonus
            + type_bonus
            + time_bonus
        )
        return max(0.0, min(1.0, match_quality))

    async def find_best_match(
        self, player1: QueuePlayer, players_queue: List[QueuePlayer]
    ) -> Optional[QueuePlayer]:
        """
        Find the best match for a player from the queue
        Returns None if no satisfactory matches are found.
        """
        try:
            best_match = None
            best_score = 0.0
            satisfactory_matches = []

            for candidate in players_queue:
                if candidate.player_id == player1.player_id:
                    continue

                match_score = await self.rate_player_pair(player1, candidate)

                if match_score >= self.settings.quality_threshold:
                    satisfactory_matches.append((candidate, match_score))

                    if match_score > best_score:
                        best_score = match_score
                        best_match = candidate

            if satisfactory_matches:
                return best_match
            else:
                self.logger.debug(
                    f"No satisfactory matches found for player {player1.player_id}"
                )
                return None

        except Exception as e:
            self.logger.error(
                f"Error finding match for player {player1.player_id}: {e}"
            )
            return None

    async def process_matchmaking(
        self,
    ) -> List[Tuple[QueuePlayer, QueuePlayer]]:
        """Process the matchmaking queue and find suitable pairs"""
        try:
            players_queue = await self.get_players_in_queue()
            if len(players_queue) < 2:
                self.logger.info("Not enough players in queue for matchmaking")
                return []

            self.logger.info(
                f"Processing matchmaking for {len(players_queue)} players"
            )

            matched_pairs = []
            processed_players = set()

            # Sort players by join time for consistent matching
            players_queue.sort(key=lambda x: x.joined_at)

            for player in players_queue:
                if player.player_id in processed_players:
                    continue

                # Find a match for this player
                match = await self.find_best_match(player, players_queue)

                if match and match.player_id not in processed_players:
                    # Found a match!
                    matched_pairs.append((player, match))
                    processed_players.add(player.player_id)
                    processed_players.add(match.player_id)

                    # Remove matched players from queue
                    await self.remove_player_from_queue(player.player_id)
                    await self.remove_player_from_queue(match.player_id)

                    self.logger.info(
                        f"Matched players {player.player_id} and {match.player_id}"
                    )

            return matched_pairs
        except Exception as e:
            self.logger.error(f"Error processing matchmaking: {e}")
            return []

    async def notify_main_process(
        self, matched_pairs: List[Tuple[QueuePlayer, QueuePlayer]]
    ) -> None:
        """Notify main process about matched pairs"""
        try:
            for player1, player2 in matched_pairs:
                match_result = MatchResult(
                    player1_id=player1.player_id,
                    player2_id=player2.player_id,
                    player1_data=player1.data,
                    player2_data=player2.data,
                    match_quality=await self.rate_player_pair(
                        player1, player2
                    ),
                )

                match_dict = match_result.model_dump()

                self.logger.info(
                    f"Match found: {player1.player_id} vs {player2.player_id} "
                    f"(quality: {match_dict['match_quality']:.2f})"
                )
                requests.post(
                    "http://bot:8000/match",
                    json={
                        "secret_key": self.settings.secret_key,
                        "player1": player1.player_id,
                        "player2": player2.player_id,
                        "quality": match_dict["match_quality"],
                    },
                )

                match_json = match_result.model_dump_json()
                self.redis.lpush(self.matches_key, match_json)

        except Exception as e:
            self.logger.error(f"Error notifying main process: {e}")

    async def restore_queue_state(self) -> None:
        """Restore matchmaking queue state on service startup"""
        try:
            queue_size = self.redis.zcard(self.queue_key)
            if queue_size > 0:
                self.logger.info(
                    f"Restored {queue_size} players in matchmaking queue after restart"
                )

                players = await self.get_players_in_queue()
                valid_players = 0
                for player in players:
                    try:
                        QueuePlayer(**player.model_dump())
                        valid_players += 1
                    except Exception as e:
                        self.logger.warning(
                            f"Removing invalid player data from queue: {e}"
                        )
                        await self.remove_player_from_queue(player.player_id)

                self.logger.info(f"Validated {valid_players} players in queue")
            else:
                self.logger.info("No players in queue on service startup")
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
                    f"Matchmaking cycle completed: {len(matched_pairs)} pairs matched"
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

    async def get_player_by_id(self, player_id: int) -> Optional[QueuePlayer]:
        """Get a specific player from the queue by ID"""
        players = await self.get_players_in_queue()
        for player in players:
            if player.player_id == player_id:
                return player
        return None

    async def update_player_rating(
        self, player_id: int, new_rating: float
    ) -> bool:
        """Update a player's rating in the queue"""
        try:
            player = await self.get_player_by_id(player_id)
            if not player:
                return False

            await self.remove_player_from_queue(player_id)

            updated_data = player.data.model_dump()
            updated_data["rating"] = new_rating
            updated_player = QueuePlayer.create(player_id, updated_data)

            player_json = updated_player.model_dump_json()
            result = self.redis.zadd(self.queue_key, {player_json: new_rating})

            return bool(result)
        except Exception as e:
            self.logger.error(f"Error updating player {player_id} rating: {e}")
            return False
