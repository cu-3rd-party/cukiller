import asyncio
import importlib
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from db.backend import init_db

TOKEN = os.getenv("TOKEN")
if TOKEN is None:
    raise Exception("Null token provided")


def get_routers(basedir=os.path.join(os.getcwd(), "handlers")):
    for root, dirs, files in os.walk(basedir):
        if not root.endswith("handlers"):
            continue
        return [importlib.import_module(f"handlers.{f.replace('.py', '')}").router for f in files if f != "__init__.py"]
    return None

async def main() -> None:
    dp = Dispatcher()

    dp.include_routers(*get_routers())

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    asyncio.run(main())
