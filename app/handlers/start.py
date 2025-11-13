# app/handlers/start.py
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.config import settings
from app.db.session import get_session
from app.services.limits import get_or_create_user
from app.keyboards import inline_start_keyboard, reply_main_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    moscow_now = datetime.now(ZoneInfo(settings.moscow_tz))

    async with await get_session() as session:
        await get_or_create_user(
            session=session,
            tg_user_id=message.from_user.id,
            username=message.from_user.username,
            now_moscow=moscow_now,
        )

    is_admin = message.from_user.id == settings.admin_id

    text = "Привет, друг👋 Хочешь списать? Тогда я вам помогу 🔥 (By iluxa)"

    await message.answer(
        text,
        reply_markup=inline_start_keyboard(),
    )

    await message.answer(
        "Кнопка главного меню всегда доступна ниже 👇",
        reply_markup=reply_main_keyboard(is_admin=is_admin),
    )