# app/database.py

import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

# URL базы берём из переменной окружения
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL не задан в переменных окружения")

# Движок и фабрика сессий
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# База для моделей
Base = declarative_base()


async def init_db() -> None:
    """
    Создаёт все таблицы и гарантирует,
    что в таблице tasks есть колонка telegram_file_id.
    """
    async with engine.begin() as conn:
        # Создаём таблицы по моделям (User, Task и т.п.)
        await conn.run_sync(Base.metadata.create_all)

        # Добавляем колонку telegram_file_id, если её нет
        await conn.execute(
            text(
                """
                ALTER TABLE tasks
                ADD COLUMN IF NOT EXISTS telegram_file_id VARCHAR(255)
                """
            )
        )
