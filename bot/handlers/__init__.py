import pkgutil
from importlib import import_module

from aiogram import Router

router = Router()

for module_info in pkgutil.iter_modules(__path__):
    if module_info.name.startswith("_") or module_info.name == "__init__":
        continue
    module = import_module(f"{__name__}.{module_info.name}")
    sub_router = getattr(module, "router", None)
    if isinstance(sub_router, Router):
        router.include_router(sub_router)
