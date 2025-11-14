# app/services/limits.py
from datetime import datetime, date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, DailyUsage


class DailyLimitExceeded(Exception):
    pass


async def get_or_create_user(
    session: AsyncSession,
    tg_user_id: int,
    username: str | None,
    now_moscow: datetime,
) -> User:
    stmt = select(User).where(User.telegram_user_id == tg_user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_user_id=tg_user_id,
            username=username,
            first_seen_at=now_moscow,
            is_premium=False,
            premium_since=None,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


async def check_and_increment_daily_usage(
    session: AsyncSession,
    user: User,
    now_moscow: datetime,
    daily_limit: int,
) -> None:
    """Кидает DailyLimitExceeded, если превышен лимит для НЕ премиумов."""
    if user.is_premium:
        return

    today = date(
        year=now_moscow.year,
        month=now_moscow.month,
        day=now_moscow.day,
    )
    stmt = select(DailyUsage).where(
        DailyUsage.user_id == user.id,
        DailyUsage.date == today,
    )
    result = await session.execute(stmt)
    usage = result.scalar_one_or_none()

    if usage is None:
        usage = DailyUsage(
            user_id=user.id,
            date=today,
            used_requests=0,
        )
        session.add(usage)
        await session.commit()
        await session.refresh(usage)

    if usage.used_requests >= daily_limit:
        raise DailyLimitExceeded()

    usage.used_requests += 1
    await session.commit()
