from sqlalchemy import Column, Integer, BigInteger, Boolean, String
from db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    chat_id = Column(BigInteger, nullable=True)
    role = Column(Integer, default=0) # 0 - regular user, 1 - admin
