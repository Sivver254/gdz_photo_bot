# app/handlers/profile.py
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.config import settings
from app.db.models import User
from app.db.session import get_session
from app.services.limits import get_or_create_user

router = Router()


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    async with await get_session() as session:
        stmt = select(User).where(User.telegram_user_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    if not user:
        moscow_now = datetime.now(ZoneInfo(settings.moscow_tz))
        async with await get_session() as session:
            user = await get_or_create_user(
                session,
                tg_user_id=message.from_user.id,
                username=message.from_user.username,
                now_moscow=moscow_now,
            )

    moscow_tz = ZoneInfo(settings.moscow_tz)
    first_seen_msk = user.first_seen_at.astimezone(moscow_tz)
    date_str = first_seen_msk.strftime("%d.%m.%Y %H:%M")

    premium_line = "Премиум: активен✅" if user.is_premium else "Премиум: отсутствует❌"

    text = f"Дата регистрации: {date_str} (по МСК)\n{premium_line}"

    await message.answer(text)