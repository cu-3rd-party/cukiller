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
RULES_PROFILE = texts.get("rules.profile")
RULES_GAMEPLAY = texts.get("rules.game")


def _strip_html(text: str) -> str:
    replacements = {
        "<br>": "\n",
        "<br/>": "\n",
        "<br />": "\n",
        "<b>": "",
        "</b>": "",
        "<i>": "",
        "</i>": "",
        "<u>": "",
        "</u>": "",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


router.include_router(
    Dialog(
        Window(
            Const(_strip_html(RULES)),
            Cancel(Const(texts.get("buttons.back"))),
            state=RulesStates.rules,
        ),
        Window(
            Const(_strip_html(RULES_GAMEPLAY)),
            Cancel(Const(texts.get("buttons.back"))),
            state=RulesStates.gameplay,
        ),
        Window(
            Const(_strip_html(RULES_PROFILE)),
            Cancel(Const(texts.get("buttons.back"))),
            state=RulesStates.profile_rules,
        ),
    )
)
