# app/handlers/start.py
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import Message

from app.config import settings
from app.db.session import get_session
from app.services.limits import get_or_create_user
from app.keyboards import inline_start_keyboard, reply_main_keyboard

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    if not message.from_user:
        return

    now_moscow = datetime.now(ZoneInfo(settings.moscow_tz))

    async with get_session() as session:
        user = await get_or_create_user(
            session=session,
            tg_user_id=message.from_user.id,
            username=message.from_user.username,
            now_moscow=now_moscow,
        )

    text = 'Привет, друг👋 Хочешь списать? Тогда я вам помогу 🔥 (By iluxa)'

    await message.answer(
        text,
        reply_markup=inline_start_keyboard(),
    )

    await message.answer(
        "Главное меню всегда доступно на клавиатуре снизу.",
        reply_markup=reply_main_keyboard(
            is_admin=(message.from_user.id == settings.admin_id)
        ),
    )
