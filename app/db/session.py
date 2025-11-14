# app/db/session.py

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.db.models import Base


# URL к базе, берём из настроек
DATABASE_URL = settings.database_url

# Асинхронный движок SQLAlchemy
engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # лишний шум в логах не нужен
    future=True,
)

# Фабрика сессий
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Используется в репозиториях/сервисах
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


# Вызываем при старте бота
async def init_db() -> None:
    """
    Создаёт таблицы и гарантирует,
    что в таблице tasks есть колонка telegram_file_id.
    """
    async with engine.begin() as conn:
        # создаём все таблицы по моделям
        await conn.run_sync(Base.metadata.create_all)

        # добавляем колонку для telegram_file_id, если её ещё нет
        await conn.execute(
            text(
                """
                ALTER TABLE tasks
                ADD COLUMN IF NOT EXISTS telegram_file_id VARCHAR(255)
                """
            )
        )
