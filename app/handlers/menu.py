# app/handlers/menu.py
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.db.models import User
from app.db.session import get_session
from app.keyboards import (
    inline_main_menu_keyboard,
    inline_premium_contact_keyboard,
)

router = Router()


@router.message(F.text == "Главное меню🏠")
async def main_menu_from_keyboard(message: Message):
    await show_main_menu(message)


@router.callback_query(F.data == "go_main_menu")
async def main_menu_from_callback(callback: CallbackQuery):
    await show_main_menu(callback.message)
    await callback.answer()


async def show_main_menu(message: Message | None):
    if not message:
        return
    await message.answer(
        "Главное меню:",
        reply_markup=inline_main_menu_keyboard(),
    )


@router.callback_query(F.data == "menu_rules")
async def menu_rules(callback: CallbackQuery):
    await callback.message.answer(
        "Привет! это важная информация для тебя❗\n"
        "Самое главное правило — не кидать бота другому классу или другу/подруге, "
        "даже если он тебе очень близкий. Бот рассчитан только на онлайн нашего класса, "
        "и если пользователей будет слишком много, он может сломаться и перестать работать.\n"
        "В целом всё главное написал — это бот только для вас!"
    )
    await callback.answer()


@router.callback_query(F.data == "menu_premium")
async def menu_premium(callback: CallbackQuery):
    await callback.message.answer(
        "Премиум доступен только тем пользователям, которые купили его у Ильи.\n"
        "Если есть вопросы или хочешь купить премиум — пиши Илюхе👇",
        reply_markup=inline_premium_contact_keyboard(),
    )
    await callback.answer()
