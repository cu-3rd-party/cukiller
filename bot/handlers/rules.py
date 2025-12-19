import logging

from aiogram import Router
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Cancel
from aiogram_dialog.widgets.text import Const

from services import texts
from services.states.rules import RulesStates

logger = logging.getLogger(__name__)

router = Router()

RULES = texts.get("rules.body")

router.include_router(
    Dialog(
        Window(Const(RULES), Cancel(Const(texts.get("buttons.back"))), state=RulesStates.rules),
    )
)
