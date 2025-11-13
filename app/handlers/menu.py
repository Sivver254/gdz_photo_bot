# app/handlers/menu.py
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from sqlalchemy import select

from app.config import settings
from app.keyboards import (
    inline_main_menu_keyboard,
    inline_premium_contact_keyboard,
    reply_main_keyboard,
)
from app.db.session import get_session
from app.db.models import User
from app.services.limits import get_or_create_user

router = Router()


@router.message(F.text == "Главное меню🏠")
async def show_main_menu_from_reply(message: Message):
    await message.answer(
        "Главное меню🏠",
        reply_markup=inline_main_menu_keyboard(),
    )


@router.callback_query(F.data == "go_main_menu")
async def show_main_menu_from_inline(callback: CallbackQuery):
    await callback.message.edit_text(
        "Главное меню🏠",
        reply_markup=inline_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu_rules")
async def rules(callback: CallbackQuery):
    text = (
        "Привет! это важная информация для тебя❗\n"
        "Самое главное правило — не кидать бота другому классу или другу/подруге, "
        "даже если он тебе очень близкий. Бот рассчитан только на онлайн нашего класса, "
        "и если пользователей будет слишком много, он может сломаться и перестать работать.\n"
        "В целом всё главное написал — это бот только для вас!"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "menu_premium")
async def premium_info(callback: CallbackQuery):
    text = (
        "Премиум доступен только тем пользователям, которые купили его у Ильи.\n"
        "Если есть вопросы или хочешь купить премиум — пиши Илюхе👇"
    )
    await callback.message.answer(text, reply_markup=inline_premium_contact_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu_profile")
async def menu_profile(callback: CallbackQuery):
    async with await get_session() as session:
        stmt = select(User).where(User.telegram_user_id == callback.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    if not user:
        moscow_now = datetime.now(ZoneInfo(settings.moscow_tz))
        async with await get_session() as session:
            user = await get_or_create_user(
                session,
                tg_user_id=callback.from_user.id,
                username=callback.from_user.username,
                now_moscow=moscow_now,
            )

    moscow_tz = ZoneInfo(settings.moscow_tz)
    first_seen_msk = user.first_seen_at.astimezone(moscow_tz)
    date_str = first_seen_msk.strftime("%d.%m.%Y %H:%M")

    premium_line = "Премиум: активен✅" if user.is_premium else "Премиум: отсутствует❌"

    text = f"Дата регистрации: {date_str} (по МСК)\n{premium_line}"

    await callback.message.answer(text)
    await callback.answer()


@router.message()
async def ensure_reply_keyboard(message: Message):
    """
    На всякий случай всегда возвращаем клавиатуру с главной кнопкой,
    если её нет.
    """
    is_admin = message.from_user.id == settings.admin_id
    if message.text and message.text not in ("Главное меню🏠", "Админ-Панель💎"):
        await message.answer(
            "Если что, главное меню всегда под рукой 👇",
            reply_markup=reply_main_keyboard(is_admin=is_admin),
        )