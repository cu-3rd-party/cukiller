import sys
import unittest
from types import ModuleType, SimpleNamespace

from bot.handlers.mainloop.getters import get_advanced_info


def _install_stub_modules() -> None:
    aiogram = ModuleType("aiogram")
    aiogram_enums = ModuleType("aiogram.enums")
    aiogram_enums.ContentType = SimpleNamespace(PHOTO="photo")
    aiogram.enums = aiogram_enums

    aiogram_dialog = ModuleType("aiogram_dialog")
    aiogram_dialog_api = ModuleType("aiogram_dialog.api")
    aiogram_dialog_entities = ModuleType("aiogram_dialog.api.entities")
    aiogram_dialog_entities.MediaAttachment = SimpleNamespace
    aiogram_dialog_entities.MediaId = SimpleNamespace
    aiogram_dialog_api.entities = aiogram_dialog_entities
    aiogram_dialog.api = aiogram_dialog_api

    handlers = ModuleType("handlers")
    registration_dialog = ModuleType("handlers.registration_dialog")
    registration_dialog.COURSE_TYPES = {
        "bachelor": "Бакалавр",
        "master": "Магистр",
        "worker": "Сотрудник ЦУ",
    }
    handlers.registration_dialog = registration_dialog

    services = ModuleType("services")

    class _Texts:
        PROFILE_FIELD_LABELS = {
            "type": "Тип",
            "course_number": "Курс",
            "group_name": "Группа",
            "about_user": "О себе",
            "allow_hugging_on_kill": "Обнимашки",
        }

        @staticmethod
        def get(key: str) -> str:
            if key == "common.unknown":
                return "Неизвестно"
            if key == "profile.hugs_allowed_yes":
                return "Да"
            if key == "profile.hugs_allowed_no":
                return "Нет"
            return key

    services.MatchmakingService = SimpleNamespace
    services.format_exit_cooldown = lambda *args, **kwargs: ""
    services.is_exit_cooldown_active = lambda *args, **kwargs: False

    def _log_getter(*args, **kwargs):
        def _decorator(func):
            return func

        return _decorator

    services.log_getter = _log_getter
    services.settings = SimpleNamespace(timezone=None)
    services.texts = _Texts()
    services.trim_name = lambda value, *_: value
    services_backend_api = ModuleType("services.backend_api")
    services_backend_api.backend_api = SimpleNamespace()

    sys.modules.setdefault("aiogram", aiogram)
    sys.modules.setdefault("aiogram.enums", aiogram_enums)
    sys.modules.setdefault("aiogram_dialog", aiogram_dialog)
    sys.modules.setdefault("aiogram_dialog.api", aiogram_dialog_api)
    sys.modules.setdefault("aiogram_dialog.api.entities", aiogram_dialog_entities)
    sys.modules.setdefault("handlers", handlers)
    sys.modules.setdefault("handlers.registration_dialog", registration_dialog)
    sys.modules.setdefault("services", services)
    sys.modules.setdefault("services.backend_api", services_backend_api)


_install_stub_modules()


class GetAdvancedInfoTests(unittest.TestCase):
    def _user(self, **overrides):
        data = {
            "type": "",
            "course_number": None,
            "group_name": "",
            "about_user": "",
            "allow_hugging_on_kill": None,
        }
        data.update(overrides)
        return SimpleNamespace(**data)

    def test_get_advanced_info_handles_empty_type(self):
        user = self._user(type="")
        result = get_advanced_info(user)
        self.assertIn("Тип", result)
        self.assertIn("Неизвестно", result)

    def test_get_advanced_info_renders_known_type(self):
        user = self._user(type="bachelor", course_number=1)
        result = get_advanced_info(user)
        self.assertIn("Тип", result)
        self.assertIn("бакалавр", result.lower())


if __name__ == "__main__":
    unittest.main()
