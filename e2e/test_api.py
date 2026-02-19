import json
import os
import time
import uuid
import unittest
from datetime import datetime, timedelta, timezone

import httpx


def _unique_int(seed: int = 0) -> int:
    return int(time.time() * 1000) + (uuid.uuid4().int % 100000) + seed


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _future_iso(days: int = 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _first_json(text: str):
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(text.lstrip())
    return obj


def _get_field(payload: dict, *names, default=None):
    for name in names:
        if name in payload:
            return payload[name]
    return default

class APITestCase(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_url = os.getenv("API_BASE_URL", "http://localhost:8080")
        cls.secret_key = os.getenv("SECRET_KEY", "very-secret-key")
        cls.headers = {"secret-key": cls.secret_key}

    async def asyncSetUp(self) -> None:
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=20.0)

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def _create_user(self, suffix: int = 0):
        payload = {
            "tg_id": _unique_int(suffix),
            "tg_username": f"test_user_{uuid.uuid4().hex[:8]}",
            "given_name": "Test",
            "family_name": "User",
            "allow_hugging_on_kill": True,
            "family_name_required": False,
            "is_in_game": False,
            "is_admin": False,
            "status": "active",
        }
        resp = await self.client.post("/users", json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return _first_json(resp.text)

    async def _create_game(self):
        payload = {
            "name": f"Game {uuid.uuid4().hex[:8]}",
            "start_date": _now_iso(),
            "end_date": _future_iso(10),
        }
        resp = await self.client.post("/games", json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return _first_json(resp.text)

    async def _create_player(self, user_id: str, game_id: str):
        payload = {"user_id": user_id, "game_id": game_id, "rating": 1000}
        resp = await self.client.post("/players", json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return _first_json(resp.text)

    async def _create_kill_event(self, game_id: str, killer_id: str, victim_id: str):
        payload = {
            "game_id": game_id,
            "killer_id": killer_id,
            "victim_id": victim_id,
            "status": "pending",
        }
        resp = await self.client.post("/kill-events", json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return _first_json(resp.text)

    async def _create_pending_profile(self, user_id: str):
        payload = {
            "user_id": user_id,
            "is_new_profile": True,
            "changed_fields": ["given_name"],
            "given_name": "Updated",
        }
        resp = await self.client.post("/pending-profiles", json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return _first_json(resp.text)

    async def _create_chat(self):
        payload = {
            "chat_id": _unique_int(),
            "key": f"chat_{uuid.uuid4().hex[:8]}",
        }
        resp = await self.client.post("/chats", json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        return _first_json(resp.text)

    async def test_health(self):
        client = httpx.AsyncClient(base_url=self.base_url, timeout=20.0)
        try:
            resp = await client.get("/health/")
            self.assertEqual(resp.status_code, 200, resp.text)
            body = _first_json(resp.text)
            self.assertIn("status", body)
            self.assertIn("timestamp", body)
        finally:
            await client.aclose()

    async def test_system_bootstrap(self):
        payload = {
            "admin_chat_id": _unique_int(1),
            "discussion_chat_id": _unique_int(2),
            "admin_tg_ids": [_unique_int(10), _unique_int(11)],
        }
        resp = await self.client.post("/system/bootstrap", json=payload)
        self.assertEqual(resp.status_code, 200, resp.text)
        body = _first_json(resp.text)
        self.assertIn("status", body)

    async def test_users_flow(self):
        created = await self._create_user()
        user_id = _get_field(created, "id", "Id")
        tg_id = _get_field(created, "tg_id", "TgId")
        self.assertIsNotNone(user_id, created)
        self.assertIsNotNone(tg_id, created)

        resp = await self.client.get(f"/users/{user_id}")
        self.assertEqual(resp.status_code, 200, resp.text)

        resp = await self.client.get(f"/users/by-tg/{tg_id}")
        self.assertEqual(resp.status_code, 200, resp.text)

        update_payload = {"given_name": "Updated"}
        resp = await self.client.patch(f"/users/{user_id}", json=update_payload)
        self.assertEqual(resp.status_code, 200, resp.text)
        updated = _first_json(resp.text)
        self.assertEqual(_get_field(updated, "given_name", "GivenName"), "Updated")

        resp = await self.client.post("/users/get-or-create", json={"tg_id": tg_id})
        self.assertIn(resp.status_code, (200, 201), resp.text)

        resp = await self.client.get("/users", params={"limit": 10, "offset": 0})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = _first_json(resp.text)
        self.assertIn("items", body)

        resp = await self.client.get("/users/count", params={"status": "active"})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = _first_json(resp.text)
        self.assertIn("total", body)

        resp = await self.client.post("/users/bulk", json={"ids": [user_id]})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = _first_json(resp.text)
        self.assertIn(user_id, body)

    async def test_games_flow(self):
        game = await self._create_game()
        game_id = _get_field(game, "id", "Id")
        self.assertIsNotNone(game_id, game)

        resp = await self.client.get(f"/games/{game_id}")
        self.assertEqual(resp.status_code, 200, resp.text)

        resp = await self.client.patch(f"/games/{game_id}", json={"name": "Updated Game"})
        self.assertEqual(resp.status_code, 200, resp.text)
        updated = _first_json(resp.text)
        self.assertEqual(_get_field(updated, "name", "Name"), "Updated Game")

        resp = await self.client.get("/games", params={"limit": 10, "offset": 0})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = _first_json(resp.text)
        self.assertIn("items", body)

        resp = await self.client.get("/games/count")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = _first_json(resp.text)
        self.assertIn("total", body)

        resp = await self.client.get("/games/active")
        self.assertIn(resp.status_code, (200, 404), resp.text)

    async def test_players_and_participants_flow(self):
        user = await self._create_user(1)
        game = await self._create_game()

        user_id = _get_field(user, "id", "Id")
        game_id = _get_field(game, "id", "Id")
        self.assertIsNotNone(user_id, user)
        self.assertIsNotNone(game_id, game)
        player = await self._create_player(user_id, game_id)
        player_id = _get_field(player, "id", "Id")
        self.assertIsNotNone(player_id, player)

        resp = await self.client.get(f"/players/{player_id}")
        self.assertEqual(resp.status_code, 200, resp.text)

        resp = await self.client.patch(f"/players/{player_id}", json={"rating": 1200})
        self.assertEqual(resp.status_code, 200, resp.text)
        updated = _first_json(resp.text)
        self.assertEqual(_get_field(updated, "rating", "Rating"), 1200)

        resp = await self.client.get("/players", params={"game_id": game_id})
        self.assertEqual(resp.status_code, 200, resp.text)
        items = _first_json(resp.text).get("items", [])
        self.assertTrue(any(_get_field(item, "id", "Id") == player_id for item in items))

        resp = await self.client.get("/players/count", params={"game_id": game_id})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = _first_json(resp.text)
        self.assertIn("total", body)

        resp = await self.client.get(f"/games/{game_id}/participants")
        self.assertEqual(resp.status_code, 200, resp.text)
        items = _first_json(resp.text).get("items", [])
        self.assertTrue(any(_get_field(item, "id", "Id") == user_id for item in items))

        resp = await self.client.get(f"/games/{game_id}/participants/count")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = _first_json(resp.text)
        self.assertIn("total", body)

    async def test_kill_events_flow(self):
        game = await self._create_game()
        killer = await self._create_user(2)
        victim = await self._create_user(3)

        game_id = _get_field(game, "id", "Id")
        killer_id = _get_field(killer, "id", "Id")
        victim_id = _get_field(victim, "id", "Id")
        self.assertIsNotNone(game_id, game)
        self.assertIsNotNone(killer_id, killer)
        self.assertIsNotNone(victim_id, victim)
        event = await self._create_kill_event(game_id, killer_id, victim_id)
        event_id = _get_field(event, "id", "Id")
        self.assertIsNotNone(event_id, event)

        resp = await self.client.get(f"/kill-events/{event_id}")
        self.assertEqual(resp.status_code, 200, resp.text)

        resp = await self.client.patch(
            f"/kill-events/{event_id}",
            json={"status": "confirmed", "killer_confirmed": True, "victim_confirmed": True},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        updated = _first_json(resp.text)
        self.assertEqual(_get_field(updated, "status", "Status"), "confirmed")

        resp = await self.client.get("/kill-events", params={"game_id": game_id})
        self.assertEqual(resp.status_code, 200, resp.text)
        items = _first_json(resp.text).get("items", [])
        self.assertTrue(any(_get_field(item, "id", "Id") == event_id for item in items))

        resp = await self.client.post(
            "/kill-events/bulk-update",
            json={"ids": [event_id], "update": {"status": "confirmed"}},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = _first_json(resp.text)
        self.assertTrue("total" in body or "count" in body, body)

    async def test_pending_profiles_flow(self):
        user = await self._create_user(4)
        user_id = _get_field(user, "id", "Id")
        self.assertIsNotNone(user_id, user)
        pending = await self._create_pending_profile(user_id)
        pending_id = _get_field(pending, "id", "Id")
        self.assertIsNotNone(pending_id, pending)

        resp = await self.client.get(f"/pending-profiles/{pending_id}")
        self.assertEqual(resp.status_code, 200, resp.text)

        resp = await self.client.patch(
            f"/pending-profiles/{pending_id}",
            json={"status": "approved", "reason": "ok"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        updated = _first_json(resp.text)
        self.assertEqual(_get_field(updated, "status", "Status"), "approved")

        resp = await self.client.get("/pending-profiles", params={"user_id": user_id})
        self.assertEqual(resp.status_code, 200, resp.text)
        items = _first_json(resp.text).get("items", [])
        self.assertTrue(any(_get_field(item, "id", "Id") == pending_id for item in items))

    async def test_chats_flow(self):
        chat = await self._create_chat()

        chat_key = _get_field(chat, "key", "Key")
        chat_id = _get_field(chat, "chat_id", "ChatId")
        self.assertIsNotNone(chat_key, chat)
        self.assertIsNotNone(chat_id, chat)

        resp = await self.client.get(f"/chats/by-key/{chat_key}")
        self.assertEqual(resp.status_code, 200, resp.text)

        resp = await self.client.get(f"/chats/by-id/{chat_id}")
        self.assertEqual(resp.status_code, 200, resp.text)


if __name__ == "__main__":
    unittest.main()
