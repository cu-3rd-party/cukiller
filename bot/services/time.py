from datetime import datetime, timedelta

from services import settings


def human_time(ts: datetime) -> str:
    ts_local = ts.astimezone(settings.timezone)
    now = datetime.now(settings.timezone)

    if ts_local.date() == now.date():
        return ts_local.strftime("Сегодня %H:%M")
    if ts_local.date() == (now.date() - timedelta(days=1)):
        return ts_local.strftime("Вчера %H:%M")
    return ts_local.strftime("%d.%m %H:%M")
