import asyncio
import contextlib
import logging
from datetime import datetime, timedelta

from aiogram import Bot

from db.models import Chat, KillEvent, Player
from services import settings, texts
from services.kills_confirmation import add_back_to_queues

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
            except Exception as exc:
                logger.exception("Проверка дедлайна, вызвало ошибку: %s", exc)
            await asyncio.sleep(self.interval_seconds)

    async def _process_timeouts(self) -> None:
        if not self._bot:
            logger.warning("KillTimeoutMonitor нету инстанса бота")
            return

        cutoff = datetime.now(settings.timezone) - self.deadline
        events = await KillEvent.filter(status="pending", created_at__lt=cutoff).prefetch_related(
            "killer",
            "victim",
            "game",
        )

        if not events:
            return

        discussion_chat = await Chat.get_or_none(key="discussion")

        for event in events:
            if event.game and event.game.end_date:
                event.status = self.timeout_status
                await event.save()
                logger.info("KillEvent %s отменено, так как игра закончилась", event.id)
                continue

            killer_player = await Player.get_or_none(game_id=event.game_id, user_id=event.killer_id)
            victim_player = await Player.get_or_none(game_id=event.game_id, user_id=event.victim_id)

            if not killer_player or not victim_player:
                logger.warning("Отсутствуют записи об игроках для KillEvent %s", event.id)
                event.status = self.timeout_status
                await event.save()
                continue

            await add_back_to_queues(event.killer, event.victim, killer_player, victim_player)
            event.status = self.timeout_status
            await event.save()
            await self._notify_participants(event, discussion_chat)

    async def _notify_participants(self, event: KillEvent, discussion_chat: Chat | None) -> None:
        killer = event.killer
        victim = event.victim

        try:
            await self._bot.send_message(
                chat_id=victim.tg_id,
                text=texts.render("timeout.victim", days=self.deadline.days),
            )
        except Exception as exc:
            logger.warning("Ошибка уведомления жертвы (%s) о таймауте, ошибка: %s", victim.id, exc)

        try:
            await self._bot.send_message(
                chat_id=killer.tg_id,
                text=texts.render("timeout.killer", days=self.deadline.days),
            )
        except Exception as exc:
            logger.warning("Ошибка уведомления киллера (%s) о таймауте, ошибка: %s", killer.id, exc)

        if discussion_chat:
            try:
                await self._bot.send_message(
                    chat_id=discussion_chat.chat_id,
                    text=texts.render(
                        "timeout.discussion",
                        killer=killer.mention_html(),
                        victim=victim.mention_html(),
                        days=self.deadline.days,
                    ),
                )
            except Exception as exc:
                logger.warning("Ошибка уведомления в дисскусию (%s) о таймауте, ошибка: %s", event.id, exc)
        else:
            logger.warning("Чат для обсуждений не настроен; пропуск уведомления о таймауте публичного сообщения")


kill_timeout_monitor = KillTimeoutMonitor()
