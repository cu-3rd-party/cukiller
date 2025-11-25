from dataclasses import dataclass

from db.models import Game, Player, User, KillEvent
from services.strings import trim_name, format_timedelta


@dataclass
class CreditsInfo:
    name: str
    duration: str
    rating_top: str
    killers_top: str
    victims_top: str
    top_players_count: int = 3

    @classmethod
    async def from_game(cls, game: Game, top_count: int = 3) -> "CreditsInfo":
        players = (
            await Player.filter(game_id=game.id)
            .order_by("-rating")
            .limit(top_count)
            .prefetch_related("user")
        )

        rating_top = (
            "\n".join(
                f"{i}: {trim_name(p.user.name, 20)} - {p.rating}"
                for i, p in enumerate(players, 1)
            )
            or "Нет участников"
        )

        duration = format_timedelta(game.end_date - game.start_date)

        kills = await KillEvent.filter(
            game_id=game.id, status="confirmed"
        ).values("killer_id", "victim_id")

        from collections import Counter

        killer_counts = Counter(k["killer_id"] for k in kills)
        victim_counts = Counter(k["victim_id"] for k in kills)

        top_killers_ids = [
            uid for uid, _ in killer_counts.most_common(top_count)
        ]
        top_victims_ids = [
            uid for uid, _ in victim_counts.most_common(top_count)
        ]

        users = {
            u.id: u
            for u in await User.filter(
                id__in=set(top_killers_ids + top_victims_ids)
            )
        }

        killers_top = (
            "\n".join(
                f"{i}: {trim_name(users[uid].name, 20)} — {killer_counts[uid]}"
                for i, uid in enumerate(top_killers_ids, 1)
            )
            or "Нет данных"
        )

        victims_top = (
            "\n".join(
                f"{i}: {trim_name(users[uid].name, 20)} — {victim_counts[uid]}"
                for i, uid in enumerate(top_victims_ids, 1)
            )
            or "Нет данных"
        )

        return cls(
            name=game.name,
            duration=duration,
            rating_top=rating_top,
            killers_top=killers_top,
            victims_top=victims_top,
            top_players_count=top_count,
        )
