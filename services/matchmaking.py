import logging
import sys
from typing import Any, Dict

import grpc
from google.protobuf import empty_pb2

from services import matchmaking_pb2, matchmaking_pb2_grpc, settings


class MatchmakingService:
    """Client for the matchmaking gRPC service."""

    logger = logging.getLogger("bot.matchmaking")

    def __init__(self) -> None:
        self._channel: grpc.aio.Channel | None = None
        self._stub: matchmaking_pb2_grpc.MatchmakingServiceStub | None = None
        self._target = self._normalize_target(settings.matchmaking_service_url)

    @staticmethod
    def _normalize_target(raw: str) -> str:
        normalized = raw
        for prefix in ("http://", "https://"):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
        return normalized.rstrip("/")

    async def _stub_client(self) -> matchmaking_pb2_grpc.MatchmakingServiceStub:
        if self._stub is None or self._channel is None:
            self._channel = grpc.aio.insecure_channel(self._target)
            self._stub = matchmaking_pb2_grpc.MatchmakingServiceStub(
                self._channel
            )
        return self._stub

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._stub = None

    async def healthcheck(self) -> None:
        stub = await self._stub_client()
        try:
            await stub.Ping(matchmaking_pb2.PingRequest())
        except Exception as exc:  # noqa: BLE001
            self.logger.fatal("Failed to ping matchmaking service: %s", exc)
            sys.exit(1)
        self.logger.info("Healthcheck completed successfully")

    # -------------------- QUEUE OPS --------------------

    async def add_player_to_queue(
        self, player_id: int, player_data: Dict[str, Any], queue_type: str
    ) -> bool:
        """Add player to Go service queue"""
        stub = await self._stub_client()
        queue = self._queue_type(queue_type)
        if queue is None:
            self.logger.error("Invalid queue type: %s", queue_type)
            return False

        await stub.AddPlayer(
            matchmaking_pb2.AddPlayerRequest(
                queue=queue, player=self._player_message(player_data)
            )
        )
        return True

    async def add_player_to_queues(
        self, player_id: int, player_data: Dict[str, Any]
    ) -> bool:
        """Add player to both queues"""
        stub = await self._stub_client()
        await stub.AddPlayerToQueues(
            matchmaking_pb2.AddPlayerToQueuesRequest(
                player=self._player_message(player_data)
            )
        )
        return True

    async def get_queues_length(self) -> tuple[int, int]:
        stub = await self._stub_client()
        resp = await stub.GetQueuesLength(empty_pb2.Empty())
        return int(resp.killers), int(resp.victims)

    async def get_player_by_id(self, player_id: int) -> tuple[bool, bool]:
        self.logger.debug("Getting player by id %d", player_id)
        stub = await self._stub_client()
        resp = await stub.GetPlayer(
            matchmaking_pb2.GetPlayerRequest(tg_id=player_id)
        )
        return resp.queued_killer, resp.queued_victim

    async def reset_queues(self) -> None:
        stub = await self._stub_client()
        await stub.ResetQueues(empty_pb2.Empty())

    # -------------------- HELPERS --------------------

    @staticmethod
    def _queue_type(queue_type: str):
        mapping = {
            "killer": matchmaking_pb2.QueueType.QUEUE_TYPE_KILLER,
            "victim": matchmaking_pb2.QueueType.QUEUE_TYPE_VICTIM,
        }
        return mapping.get(queue_type.lower())

    @staticmethod
    def _player_message(data: Dict[str, Any]) -> matchmaking_pb2.PlayerData:
        kwargs: Dict[str, Any] = {
            "tg_id": int(data["tg_id"]),
            "rating": int(data.get("rating", 0)),
            "type": MatchmakingService._normalize_type(data.get("type")),
            "group_name": str(data.get("group_name", "")),
        }
        if data.get("course_number") is not None:
            kwargs["course_number"] = int(data["course_number"])
        return matchmaking_pb2.PlayerData(**kwargs)

    @staticmethod
    def _normalize_type(raw: Any) -> str:
        value = str(raw or "").strip().lower()
        mapping = {
            "bachelor": "bachelor",
            "master": "master",
            "specialist": "specialist",
            "worker": "other",
            "staff": "other",
            "other": "other",
        }
        return mapping.get(value, "other")
