from aiogram import Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    BotCommand,
    BotCommandScope,
    BotCommandScopeChat,
)

from bot.filters.admin import AdminFilter
from db.models import User

router = Router()


@router.message(AdminFilter(), CommandStart())
async def admin_start(message: Message, bot: Bot):
    await bot.set_my_commands(
        commands=[
            BotCommand(command="/start", description="Начать работу с ботом"),
            BotCommand(
                command="/stats",
                description="Получить краткую статистику по боту",
            ),
        ],
        scope=BotCommandScopeChat(chat_id=message.chat.id),
    )
    await message.reply(
        text=(
            "Привет, админ!\n"
            "Добавил тебе список команд в менюшку, полюбуйся)\n"
        )
    )


@router.message(AdminFilter(), Command(commands=["stats"]))
async def stats(message: Message, bot: Bot):
    user_count = await User().all().count()
    user_confirmed_count = await User().filter(status="confirmed").count()
    await message.reply(
        text=(
            "Держи краткую статистику по боту\n\n"
            f"В базе данных сейчас находится {user_count} уникальных пользователей\n"
            f"Из них {user_confirmed_count} имеют подтвержденные профили, что составляет {user_confirmed_count / user_count * 100}%\n"
            "Другие статистики будут добавляться по ходу дела, хозяин"
        )
    )
