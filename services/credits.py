from collections import Counter
from typing import Dict, List
from uuid import UUID

from pydantic import BaseModel

from db.models import Game, Player, User, KillEvent
from services.strings import format_timedelta
from services.time import human_time


class PlayerStats(BaseModel):
    rating: int = 0
    kills: int = 0
    deaths: int = 0
    log: List[str] = []


class CreditsInfo(BaseModel):
    name: str
    duration: str
    rating_top: str
    killers_top: str
    victims_top: str
    per_player: Dict[UUID, PlayerStats]
    top_players_count: int = 3

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    async def from_game(cls, game: Game, top_count: int = 3) -> "CreditsInfo":
        players = await Player.filter(game_id=game.id).order_by("-rating").limit(top_count).prefetch_related("user")

        # Rating TOP
        rating_top = cls._format_top([(p.user, p.rating) for p in players], empty="Нет участников")

        # Game duration
        duration = format_timedelta(game.end_date - game.start_date)

        # --- Load all confirmed kill events ---
        kills = await KillEvent.filter(game_id=game.id, status="confirmed").values(
            "killer_id", "victim_id", "updated_at"
        )

        # Build counters
        killer_counts = Counter(k["killer_id"] for k in kills)
        victim_counts = Counter(k["victim_id"] for k in kills)

        # Load users for involved players
        all_user_ids = set(killer_counts) | set(victim_counts)
        users = {u.id: u for u in await User.filter(id__in=all_user_ids)}

        # Killers top / victims top
        killers_top = cls._format_top(
            [(users[uid], killer_counts[uid]) for uid, _ in killer_counts.most_common(top_count)],
            empty="Нет данных",
        )
        victims_top = cls._format_top(
            [(users[uid], victim_counts[uid]) for uid, _ in victim_counts.most_common(top_count)],
            empty="Нет данных",
        )

        # --- Per-player full stats ---
        per_player = await cls._build_player_stats(game, users, kills)

        return cls(
            name=game.name,
            duration=duration,
            rating_top=rating_top,
            killers_top=killers_top,
            victims_top=victims_top,
            per_player=per_player,
            top_players_count=top_count,
        )

    @staticmethod
    def _format_top(items: List[tuple], empty: str) -> str:
        """Formats a list of (User, value) pairs into a numbered list with HTML mentions."""
        if not items:
            return empty
        return "\n".join(f"{i}: {user.mention_html(max_len=20)} — {value}" for i, (user, value) in enumerate(items, 1))

    @staticmethod
    async def _build_player_stats(game: Game, users: Dict[int, User], kills: List[dict]) -> Dict[UUID, PlayerStats]:
        # preload all players
        all_players = await Player.filter(game_id=game.id).prefetch_related("user").all()
        stats = {p.user.id: PlayerStats(rating=p.rating) for p in all_players}

        for k in kills:
            killer_id = k["killer_id"]
            victim_id = k["victim_id"]
            ts = human_time(k["updated_at"])

            # increment stats
            stats[killer_id].kills += 1
            stats[victim_id].deaths += 1

            # logs with HTML mentions
            stats[killer_id].log.append(f"Вы убили {users[victim_id].mention_html(max_len=25)} в {ts}")
            stats[victim_id].log.append(f"Вас убил {users[killer_id].mention_html(max_len=25)} в {ts}")

        return stats
