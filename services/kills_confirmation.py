from db.models import Player, User
from services import settings
from services.matchmaking import MatchmakingService


async def modify_rating(killer_player: Player, victim_player: Player, killer_k=1, victim_k=0, p=1):
    """After successful kill, update ELO ratings of killer and victim."""
    killer_rating = killer_player.rating
    victim_rating = victim_player.rating

    expected_killer = 1 / (1 + 10 ** ((victim_rating - killer_rating) / settings.ELO_SCALE))
    expected_victim = 1 / (1 + 10 ** ((killer_rating - victim_rating) / settings.ELO_SCALE))

    killer_delta = settings.K_KILLER * (killer_k - expected_killer) * p
    victim_delta = settings.K_VICTIM * (victim_k - expected_victim) * p

    killer_new = killer_rating + killer_delta
    victim_new = victim_rating + victim_delta

    killer_player.rating = round(killer_new)
    victim_player.rating = round(victim_new)

    await killer_player.save()
    await victim_player.save()

    return killer_delta, victim_delta


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
