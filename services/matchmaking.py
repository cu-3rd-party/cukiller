import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


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
            queue_data = {
                "player_id": player_id,
                "player_data": player_data,
                "joined_at": datetime.now().isoformat(),
                "rating": player_data.get("player_rating", 0),
            }

            # Add to sorted set with rating as score for easy matching by skill
            result = self.redis.zadd(
                self.queue_key, {json.dumps(queue_data): queue_data["rating"]}
            )

            self.logger.info(
                f"Player {player_id} added to matchmaking queue with rating {queue_data['rating']}"
            )
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error adding player {player_id} to queue: {e}")
            return False

    async def remove_player_from_queue(self, player_id: int) -> bool:
        """Remove player from matchmaking queue"""
        try:
            # Find and remove the player from queue
            queue_members = self.redis.zrange(self.queue_key, 0, -1)
            for member in queue_members:
                data = json.loads(member)
                if data["player_id"] == player_id:
                    self.redis.zrem(self.queue_key, member)
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

    async def get_players_in_queue(self) -> List[Dict[str, Any]]:
        """Get all players currently in matchmaking queue"""
        try:
            queue_members = self.redis.zrange(
                self.queue_key, 0, -1, withscores=True
            )
            players = []
            for member, score in queue_members:
                player_data = json.loads(member)
                player_data["score"] = score
                players.append(player_data)
            return players
        except Exception as e:
            self.logger.error(f"Error getting players from queue: {e}")
            return []

    async def find_best_match(
        self, player1: Dict[str, Any], players_queue: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best match for a player from the queue.
        This is where you'll implement your matching formula.
        """
        try:
            # TODO: Implement matching algorithm here
            raise NotImplementedError()
        except Exception as e:
            self.logger.error(
                f"Error finding match for player {player1['player_id']}: {e}"
            )
            return None

    async def process_matchmaking(
        self,
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
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

            # Sort players by join time or rating for consistent matching
            players_queue.sort(key=lambda x: x.get("joined_at", ""))

            for player_data in players_queue:
                if player_data["player_id"] in processed_players:
                    continue

                # Find a match for this player
                match = await self.find_best_match(player_data, players_queue)

                if match and match["player_id"] not in processed_players:
                    # Found a match!
                    matched_pairs.append((player_data, match))
                    processed_players.add(player_data["player_id"])
                    processed_players.add(match["player_id"])

                    # Remove matched players from queue
                    await self.remove_player_from_queue(
                        player_data["player_id"]
                    )
                    await self.remove_player_from_queue(match["player_id"])

                    self.logger.info(
                        f"Matched players {player_data['player_id']} and {match['player_id']}"
                    )

            return matched_pairs
        except Exception as e:
            self.logger.error(f"Error processing matchmaking: {e}")
            return []

    async def notify_main_process(
        self, matched_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]]
    ) -> None:
        """Notify main process about matched pairs"""
        try:
            for player1, player2 in matched_pairs:
                match_data = {
                    "player1_id": player1["player_id"],
                    "player2_id": player2["player_id"],
                    "player1_data": player1["player_data"],
                    "player2_data": player2["player_data"],
                    "matched_at": datetime.now().isoformat(),
                    "match_quality": abs(
                        player1.get("rating", 0) - player2.get("rating", 0)
                    ),  # Your metric
                }

                # TODO: Implement main process notification mechanism
                # This could be HTTP request, message queue, database update, etc.
                self.logger.info(
                    f"Match found: {player1['player_id']} vs {player2['player_id']}"
                )

        except Exception as e:
            self.logger.error(f"Error notifying main process: {e}")

    async def restore_queue_state(self) -> None:
        """Restore matchmaking queue state on service startup"""
        try:
            # Check if there are any players that were in queue before restart
            # You might want to store queue state persistently or let players rejoin
            queue_size = self.redis.zcard(self.queue_key)
            if queue_size > 0:
                self.logger.info(
                    f"Restored {queue_size} players in matchmaking queue after restart"
                )
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

            # Process matchmaking
            matched_pairs = await self.process_matchmaking()

            # Notify main process about matches
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
