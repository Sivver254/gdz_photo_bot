# app/db/models.py
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
    premium_since = Column(DateTime(timezone=True), nullable=True)

    tasks = relationship("Task", back_populates="user")


class DailyUsage(Base):
    __tablename__ = "daily_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    used_requests = Column(Integer, nullable=False, default=0)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    is_premium = Column(Boolean, nullable=False, default=False)
    telegram_file_id = Column(String(255), nullable=True)
    answer_text = Column(Text, nullable=False)

    user = relationship("User", back_populates="tasks")
