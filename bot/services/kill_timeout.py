from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError

from services import texts
from services.backend_api import backend_api
from services.kills_confirmation import add_back_to_queues
from services.settings import settings

if TYPE_CHECKING:
    from aiogram import Bot

    from services.backend_api import Model as Chat
    from services.backend_api import Model as KillEvent

logger = logging.getLogger(__name__)


class KillTimeoutMonitor:
    def __init__(
        self,
        *,
        interval_seconds: int = 3600,
        deadline_days: int = 10,
        timeout_status: str = "timeout",
    ) -> None:
        self.interval_seconds = interval_seconds
        self.deadline = timedelta(days=deadline_days)
        self.timeout_status = timeout_status
        self._task: asyncio.Task | None = None
        self._running = False
        self._bot: Bot | None = None

    async def start(self, bot: Bot) -> None:
        if self._running:
            return

        self._bot = bot
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Запустили сервис KillTimeoutMonitor (дедлайн %s дней)", self.deadline.days)

    async def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Остановили KillTimeoutMonitor")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self._process_timeouts()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Проверка дедлайна, вызвало ошибку")
            await asyncio.sleep(self.interval_seconds)

    async def _process_timeouts(self) -> None:
        if not self._bot:
            logger.warning("KillTimeoutMonitor нету инстанса бота")
            return

        cutoff = datetime.now(settings.timezone) - self.deadline
        events = await backend_api.list_kill_events(status="pending", updated_before=cutoff)

        if not events:
            return

        discussion_chat = await backend_api.get_chat_by_key("discussion")

        for event in events:
            if event.game and event.game.end_date:
                event.status = self.timeout_status
                await backend_api.update_kill_event(event.id, {"status": event.status})
                logger.info("KillEvent %s отменено, так как игра закончилась", event.id)
                continue

            killer_players = await backend_api.list_players(game_id=event.game_id, user_id=event.killer_id)
            killer_player = killer_players[0] if killer_players else None
            victim_players = await backend_api.list_players(game_id=event.game_id, user_id=event.victim_id)
            victim_player = victim_players[0] if victim_players else None

            if not killer_player or not victim_player:
                logger.warning("Отсутствуют записи об игроках для KillEvent %s", event.id)
                event.status = self.timeout_status
                await backend_api.update_kill_event(event.id, {"status": event.status})
                continue

            if not getattr(event, "killer", None):
                event.killer = await backend_api.get_user_by_id(event.killer_id)
            if not getattr(event, "victim", None):
                event.victim = await backend_api.get_user_by_id(event.victim_id)

            await add_back_to_queues(event.killer, event.victim, killer_player, victim_player)
            event.status = self.timeout_status
            await backend_api.update_kill_event(event.id, {"status": event.status})
            await self._notify_participants(event, discussion_chat)

    async def _notify_participants(self, event: KillEvent, discussion_chat: Chat | None) -> None:
        killer = event.killer
        victim = event.victim

        try:
            await self._send_message(
                chat_id=victim.tg_id,
                text=texts.render("timeout.victim", days=self.deadline.days),
            )
        except TelegramAPIError as exc:
            logger.warning("Ошибка уведомления жертвы (%s) о таймауте, ошибка: %s", victim.id, exc)

        try:
            await self._send_message(
                chat_id=killer.tg_id,
                text=texts.render("timeout.killer", days=self.deadline.days),
            )
        except TelegramAPIError as exc:
            logger.warning("Ошибка уведомления киллера (%s) о таймауте, ошибка: %s", killer.id, exc)

        if discussion_chat:
            try:
                await self._send_message(
                    chat_id=discussion_chat.chat_id,
                    text=texts.render(
                        "timeout.discussion",
                        killer=killer.mention_html(),
                        victim=victim.mention_html(),
                        days=self.deadline.days,
                    ),
                )
            except TelegramAPIError as exc:
                logger.warning("Ошибка уведомления в дисскусию (%s) о таймауте, ошибка: %s", event.id, exc)
        else:
            logger.warning("Чат для обсуждений не настроен; пропуск уведомления о таймауте публичного сообщения")


kill_timeout_monitor = KillTimeoutMonitor()
