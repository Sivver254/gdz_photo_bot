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
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
    premium_since = Column(DateTime(timezone=True), nullable=True)

    usages = relationship("DailyUsage", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")


class DailyUsage(Base):
    __tablename__ = "daily_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    used_requests = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="usages")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    is_premium = Column(Boolean, default=False, nullable=False)
    photo_file_id = Column(String(255), nullable=True)
    answer_text = Column(Text, nullable=False)

    user = relationship("User", back_populates="tasks")