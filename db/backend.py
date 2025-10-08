import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.base import Base  # Изменено: импортируем Base из db.base
from db.models import *

DATABASE_URL = os.getenv("DATABASE_URL") if os.getenv("DATABASE_URL") else "sqlite:///bot.db"
engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def try_register_user(telegram_id: int, username: str = "", chat_id: int | None = None) -> bool:
    """
    Пытается зарегистрировать пользователя в базе данных
    :param telegram_id: уникальный айдишник пользователя
    :param username: (опционально)
    :param chat_id: (опционально) айди чата личных сообщений с юзером
    :return:
    """
    session = SessionLocal()
    try:
        user_obj = session.query(User).filter_by(chat_id=chat_id).first()
        if not user_obj:
            session.add(User(chat_id=chat_id, telegram_id=telegram_id, username=username))
            session.commit()
            return True
    finally:
        session.close()
        return False

def init_db():
    Base.metadata.create_all(bind=engine)
