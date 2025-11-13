# app/db/session.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models import Base

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

async_session_maker = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncSession:
    return async_session_maker()


async def init_db() -> None:
    """Создаёт таблицы, если их нет."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)