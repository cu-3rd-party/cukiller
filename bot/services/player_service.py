import json
from typing import Optional, Dict, Any

from db.models import Player
from settings import get_redis_client


class PlayerService:
    def __init__(self):
        self.redis_client = get_redis_client()

    @staticmethod
    def _player_to_dict(player: Player) -> Dict[str, Any]:
        """Convert Player instance to dictionary"""
        return {
            'id': player.id,
            'user_id': player.user.id,
            'game_id': player.game.id,
            'player_rating': player.player_rating,
            'player_victim_id': player.player_victim.id,
            'player_killer_id': player.player_killer.id,
            'created_at': player.created_at.isoformat() if player.created_at else None,
            'updated_at': player.updated_at.isoformat() if player.updated_at else None
        }

    @staticmethod
    def _dict_to_player_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert dictionary back to player data (for reconstruction)"""
        return {
            'id': data['id'],
            'user_id': data['user_id'],
            'game_id': data['game_id'],
            'player_rating': data['player_rating'],
            'player_victim_id': data['player_victim_id'],
            'player_killer_id': data['player_killer_id'],
            'created_at': data['created_at'],
            'updated_at': data['updated_at']
        }

    async def save_player_to_redis(self, player: Player) -> bool:
        """Save player to Redis with expiration"""
        try:
            player_data = self._player_to_dict(player)
            key = f"player:{player.id}"

            # Store as JSON
            await self.redis_client.set(
                key,
                json.dumps(player_data, default=str)
            )

            # Also index by user and game for faster lookups
            await self.redis_client.sadd(f"user_players:{player.user.id}", player.id)
            await self.redis_client.sadd(f"game_players:{player.game.id}", player.id)

            return True
        except Exception as e:
            print(f"Error saving player to Redis: {e}")
            return False

    async def get_player_from_redis(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve player data from Redis"""
        try:
            key = f"player:{player_id}"
            player_data = await self.redis_client.get(key)

            if player_data:
                return json.loads(player_data)
            return None
        except Exception as e:
            print(f"Error getting player from Redis: {e}")
            return None

    async def get_player_by_user_game(self, user_id: int, game_id: int) -> Optional[Dict[str, Any]]:
        """Get player by user and game combination"""
        try:
            # You might want to create a specific key for this unique combination
            unique_key = f"player:user:{user_id}:game:{game_id}"
            player_id = await self.redis_client.get(unique_key)

            if player_id:
                return await self.get_player_from_redis(int(player_id))
            return None
        except Exception as e:
            print(f"Error getting player by user/game: {e}")
            return None