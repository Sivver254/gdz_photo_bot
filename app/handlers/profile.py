# app/handlers/profile.py
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.config import settings
from app.db.models import User
from app.db.session import get_session
from app.services.limits import get_or_create_user

router = Router()


@router.callback_query(F.data == "menu_profile")
async def menu_profile(callback: CallbackQuery):
    """
    Показывает профиль пользователя:
    - дата регистрации (берётся из БД, не меняется)
    - статус премиума
    Если записи в БД почему-то нет — создаём её на лету.
    """
    if not callback.from_user:
        await callback.answer()
        return

    now_moscow = datetime.now(ZoneInfo(settings.moscow_tz))

    async with get_session() as session:
        # Гарантированно получаем пользователя (создаём, если не было)
        user = await get_or_create_user(
            session=session,
            tg_user_id=callback.from_user.id,
            username=callback.from_user.username,
            now_moscow=now_moscow,
        )

    # first_seen_at может быть с таймзоной или без — аккуратно форматируем
    first_seen = user.first_seen_at
    try:
        if first_seen.tzinfo is not None:
            first_seen = first_seen.astimezone(ZoneInfo(settings.moscow_tz))
    except Exception:
        # Если вдруг БД вернула кривую дату — просто оставляем как есть
        pass

    first_seen_str = first_seen.strftime("%d.%m.%Y %H:%M")
    premium_status = "активен✅" if user.is_premium else "отсутствует❌"

    text = (
        f"Дата регистрации: {first_seen_str} (по МСК)\n"
        f"Премиум: {premium_status}"
    )

    await callback.message.answer(text)
    await callback.answer()
