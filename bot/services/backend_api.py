import html
import logging
from collections.abc import Iterable
from datetime import datetime
from types import SimpleNamespace

import httpx

from services.settings import settings
from services.strings import build_full_name, trim_name

logger = logging.getLogger(__name__)

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
type SerializeValue = JsonValue | datetime | list["SerializeValue"] | dict[str, "SerializeValue"]
type Converted = "Model" | JsonValue | list["Converted"] | dict[str, "Converted"]
type QueryParamValue = str | int | float | bool

HTTP_NOT_FOUND = 404
HTTP_NO_CONTENT = 204
HTTP_CREATED = 201

_DATETIME_KEYS = {
    "created_at",
    "updated_at",
    "start_date",
    "end_date",
    "exit_cooldown_until",
    "killer_confirmed_at",
    "victim_confirmed_at",
    "moderated_at",
}


def _parse_datetime(value: str) -> datetime | str:
    if not isinstance(value, str):
        return value
    if "T" not in value:
        return value
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value)
        return datetime.fromisoformat(value)
    except ValueError:
        return value


class Model(SimpleNamespace):
    pass


class UserModel(Model):
    @property
    def full_name(self) -> str:
        return build_full_name(self.given_name, self.family_name, self.tg_username or "")

    def mention_html(self, max_len: int = 128) -> str:
        name = self.full_name or self.tg_username or str(self.tg_id)
        name = trim_name(name, max_len)
        return f'<a href="tg://user?id={self.tg_id}">{html.escape(name)}</a>'

    def profile_link(self) -> str:
        return f"tg://user?id={self.tg_id}"


class PendingProfileModel(Model):
    @property
    def full_name(self) -> str:
        return build_full_name(self.given_name, self.family_name, "")


class BackendAPI:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=settings.backend_api_url.rstrip("/"),
                headers={"secret-key": settings.secret_key},
                timeout=10.0,
            )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, QueryParamValue] | None = None,
        json_data: dict[str, SerializeValue] | None = None,
    ) -> tuple[int, JsonValue | None]:
        logger.debug("Sending %s request to %s with params=%s data=%s", method, path, params, json_data)
        if self._client is None:
            await self.start()
        if self._client is None:
            msg = "Backend API client is not initialized"
            raise RuntimeError(msg)
        payload = self._serialize(json_data) if json_data else None
        resp = await self._client.request(method, path, params=params, json=payload)
        if resp.status_code == HTTP_NOT_FOUND:
            return resp.status_code, None
        resp.raise_for_status()
        if resp.status_code == HTTP_NO_CONTENT:
            return resp.status_code, None
        if "application/json" in resp.headers.get("Content-Type", ""):
            return resp.status_code, resp.json()
        return resp.status_code, None

    def _convert(self, value: JsonValue, *, as_object: bool) -> Converted:
        if isinstance(value, list):
            return [self._convert(item, as_object=as_object) for item in value]
        if isinstance(value, dict):
            data: dict[str, Converted] = {}
            for key, val in value.items():
                if key in _DATETIME_KEYS:
                    data[key] = _parse_datetime(val)
                else:
                    data[key] = self._convert(val, as_object=as_object)
            if not as_object:
                return data
            return self._model_from_dict(data)
        return value

    def _serialize(self, value: SerializeValue) -> JsonValue:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, list):
            return [self._serialize(item) for item in value]
        if isinstance(value, dict):
            return {key: self._serialize(val) for key, val in value.items()}
        return value

    def _model_from_dict(self, data: dict[str, Converted]) -> Model:
        model_cls: type[Model] = Model
        if "tg_id" in data:
            model_cls = UserModel
        if "is_new_profile" in data and "changed_fields" in data:
            model_cls = PendingProfileModel
        return model_cls(**data)

    async def bootstrap(
        self,
        admin_chat_id: int,
        discussion_chat_id: int,
        admin_tg_ids: Iterable[int],
    ) -> Converted | None:
        _, data = await self._request(
            "POST",
            "/system/bootstrap",
            json_data={
                "admin_chat_id": admin_chat_id,
                "discussion_chat_id": discussion_chat_id,
                "admin_tg_ids": list(admin_tg_ids),
            },
        )
        return self._convert(data, as_object=True)

    async def get_or_create_user(self, payload: dict[str, SerializeValue]) -> tuple[UserModel, bool]:
        status, data = await self._request("POST", "/users/get-or-create", json_data=payload)
        user = self._convert(data, as_object=True)
        return user, status == HTTP_CREATED

    async def get_user_by_tg_id(self, tg_id: int) -> UserModel | None:
        _, data = await self._request("GET", f"/users/by-tg/{tg_id}")
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def get_user_by_id(self, user_id: str) -> UserModel | None:
        _, data = await self._request("GET", f"/users/{user_id}")
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def update_user_by_tg_id(self, tg_id: int, payload: dict[str, SerializeValue]) -> UserModel | None:
        _, data = await self._request("PATCH", f"/users/by-tg/{tg_id}", json_data=payload)
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def update_user(self, user_id: str, payload: dict[str, SerializeValue]) -> UserModel | None:
        _, data = await self._request("PATCH", f"/users/{user_id}", json_data=payload)
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def list_users(
        self,
        *,
        status: str | None = None,
        is_in_game: bool | None = None,
        is_admin: bool | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UserModel]:
        params: dict[str, QueryParamValue] = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        if is_in_game is not None:
            params["is_in_game"] = is_in_game
        if is_admin is not None:
            params["is_admin"] = is_admin
        _, data = await self._request("GET", "/users", params=params)
        if not data:
            return []
        return self._convert(data.get("items", []), as_object=True)

    async def count_users(self, *, status: str | None = None) -> int:
        params = {"status": status} if status else None
        _, data = await self._request("GET", "/users/count", params=params)
        return int((data or {}).get("total", 0))

    async def get_users_bulk(self, ids: Iterable[str]) -> dict[str, UserModel]:
        _, data = await self._request("POST", "/users/bulk", json_data={"ids": list(ids)})
        if not isinstance(data, dict):
            return {}
        return {key: self._convert(value, as_object=True) for key, value in data.items()}

    async def list_games(
        self,
        *,
        status: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[Model]:
        params: dict[str, QueryParamValue] = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        _, data = await self._request("GET", "/games", params=params)
        if not data:
            return []
        return self._convert(data.get("items", []), as_object=True)

    async def count_games(self, *, status: str | None = None) -> int:
        params = {"status": status} if status else None
        _, data = await self._request("GET", "/games/count", params=params)
        return int((data or {}).get("total", 0))

    async def get_active_game(self) -> Model | None:
        _, data = await self._request("GET", "/games/active")
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def get_game_by_id(self, game_id: str) -> Model | None:
        _, data = await self._request("GET", f"/games/{game_id}")
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def create_game(self, payload: dict[str, SerializeValue]) -> Model:
        _, data = await self._request("POST", "/games", json_data=payload)
        return self._convert(data, as_object=True)

    async def update_game(self, game_id: str, payload: dict[str, SerializeValue]) -> Model | None:
        _, data = await self._request("PATCH", f"/games/{game_id}", json_data=payload)
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def list_game_participants(self, game_id: str) -> list[UserModel]:
        _, data = await self._request("GET", f"/games/{game_id}/participants")
        if not data:
            return []
        return self._convert(data.get("items", []), as_object=True)

    async def count_game_participants(self, game_id: str) -> int:
        _, data = await self._request("GET", f"/games/{game_id}/participants/count")
        return int((data or {}).get("total", 0))

    async def list_players(
        self,
        *,
        game_id: str | None = None,
        user_id: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[Model]:
        params: dict[str, QueryParamValue] = {"limit": limit, "offset": offset}
        if game_id:
            params["game_id"] = game_id
        if user_id:
            params["user_id"] = user_id
        _, data = await self._request("GET", "/players", params=params)
        if not data:
            return []
        return self._convert(data.get("items", []), as_object=True)

    async def count_players(self, *, game_id: str | None = None) -> int:
        params = {"game_id": game_id} if game_id else None
        _, data = await self._request("GET", "/players/count", params=params)
        return int((data or {}).get("total", 0))

    async def create_player(self, payload: dict[str, SerializeValue]) -> Model:
        _, data = await self._request("POST", "/players", json_data=payload)
        return self._convert(data, as_object=True)

    async def update_player(self, player_id: str, payload: dict[str, SerializeValue]) -> Model | None:
        _, data = await self._request("PATCH", f"/players/{player_id}", json_data=payload)
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def list_kill_events(  # noqa: PLR0913
        self,
        *,
        game_id: str | None = None,
        killer_id: str | None = None,
        victim_id: str | None = None,
        status: str | None = None,
        updated_before: datetime | None = None,
        limit: int = 1000,
        offset: int = 0,
        as_object: bool = True,
    ) -> list[Converted]:
        params: dict[str, QueryParamValue] = {"limit": limit, "offset": offset}
        if game_id:
            params["game_id"] = game_id
        if killer_id:
            params["killer_id"] = killer_id
        if victim_id:
            params["victim_id"] = victim_id
        if status:
            params["status"] = status
        if updated_before:
            params["updated_before"] = updated_before.isoformat()
        _, data = await self._request("GET", "/kill-events", params=params)
        if not data:
            return []
        return self._convert(data.get("items", []), as_object=as_object)

    async def create_kill_event(self, payload: dict[str, SerializeValue]) -> Model:
        _, data = await self._request("POST", "/kill-events", json_data=payload)
        return self._convert(data, as_object=True)

    async def get_kill_event(self, kill_event_id: str) -> Model | None:
        _, data = await self._request("GET", f"/kill-events/{kill_event_id}")
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def update_kill_event(self, kill_event_id: str, payload: dict[str, SerializeValue]) -> Model | None:
        _, data = await self._request("PATCH", f"/kill-events/{kill_event_id}", json_data=payload)
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def bulk_update_kill_events(self, ids: Iterable[str], payload: dict[str, SerializeValue]) -> int:
        _, data = await self._request(
            "POST",
            "/kill-events/bulk-update",
            json_data={"ids": list(ids), "update": payload},
        )
        return int((data or {}).get("total", 0))

    async def list_pending_profiles(
        self,
        *,
        status: str | None = None,
        user_id: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[Model]:
        params: dict[str, QueryParamValue] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if user_id:
            params["user_id"] = user_id
        _, data = await self._request("GET", "/pending-profiles", params=params)
        if not data:
            return []
        return self._convert(data.get("items", []), as_object=True)

    async def create_pending_profile(self, payload: dict[str, SerializeValue]) -> Model:
        _, data = await self._request("POST", "/pending-profiles", json_data=payload)
        return self._convert(data, as_object=True)

    async def get_pending_profile(self, pending_id: str) -> Model | None:
        _, data = await self._request("GET", f"/pending-profiles/{pending_id}")
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def update_pending_profile(self, pending_id: str, payload: dict[str, SerializeValue]) -> Model | None:
        _, data = await self._request("PATCH", f"/pending-profiles/{pending_id}", json_data=payload)
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def get_chat_by_key(self, key: str) -> Model | None:
        _, data = await self._request("GET", f"/chats/by-key/{key}")
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def get_chat_by_id(self, chat_id: int) -> Model | None:
        _, data = await self._request("GET", f"/chats/by-id/{chat_id}")
        if data is None:
            return None
        return self._convert(data, as_object=True)

    async def create_chat(self, payload: dict[str, SerializeValue]) -> Model:
        _, data = await self._request("POST", "/chats", json_data=payload)
        return self._convert(data, as_object=True)


backend_api = BackendAPI()
