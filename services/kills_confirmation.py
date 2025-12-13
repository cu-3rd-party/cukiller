from db.models import Player, User
from services.matchmaking import MatchmakingService


async def add_back_to_queues(killer: User, victim: User, killer_player: Player, victim_player: Player):
    """Return both players to matchmaking queues."""
    matchmaking = MatchmakingService()
    for user, player, qtype in (
        (killer, killer_player, "killer"),
        (victim, victim_player, "victim"),
    ):
        await matchmaking.add_player_to_queue(
            user.tg_id,
            {
                "tg_id": user.tg_id,
                "rating": player.rating,
                "type": user.type,
                "course_number": user.course_number,
                "group_name": user.group_name,
            },
            queue_type=qtype,
        )
