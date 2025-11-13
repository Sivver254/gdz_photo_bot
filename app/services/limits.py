# app/services/limits.py
from __future__ import annotations

from datetime import datetime
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, DailyUsage


async def get_or_create_user(
    session: AsyncSession,
    tg_user_id: int,
    username: str | None,
    now_moscow: datetime,
) -> User:
    stmt = select(User).where(User.telegram_user_id == tg_user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        if username and user.username != username:
            user.username = username
            await session.commit()
        return user

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


async def check_and_increment_daily_limit(
    session: AsyncSession,
    user: User,
    now_moscow: datetime,
    daily_limit: int,
) -> Tuple[bool, int]:
    """
    True -> запрос разрешён, счётчик увеличен.
    False -> лимит превышен, счётчик не меняем.
    """
    if user.is_premium:
        return True, -1  # -1 как маркер "без лимита"

    current_date = now_moscow.date()
    stmt = select(DailyUsage).where(
        DailyUsage.user_id == user.id,
        DailyUsage.date == current_date,
    )
    result = await session.execute(stmt)
    usage = result.scalar_one_or_none()

    if usage is None:
        usage = DailyUsage(
            user_id=user.id,
            date=current_date,
            used_requests=1,
        )
        session.add(usage)
        await session.commit()
        return True, usage.used_requests

    if usage.used_requests >= daily_limit:
        return False, usage.used_requests

    usage.used_requests += 1
    await session.commit()
    return True, usage.used_requests