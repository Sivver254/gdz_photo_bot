# app/handlers/admin.py
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from app.config import settings
from app.db.models import User
from app.db.session import get_session
from app.keyboards import inline_admin_panel_keyboard, reply_main_keyboard

router = Router()


class AdminStates(StatesGroup):
    waiting_user_id_give = State()
    waiting_user_id_remove = State()


def _is_admin(user_id: int) -> bool:
    return user_id == settings.admin_id


@router.message(F.text == "Админ-Панель💎")
async def admin_panel_entry(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-панели❗")
        return

    await message.answer(
        "Админ-Панель, функционал полный снизу🔥",
        reply_markup=inline_admin_panel_keyboard(),
    )


@router.callback_query(F.data == "admin_give_premium")
async def admin_give_premium(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_user_id_give)
    await callback.message.answer(
        "Введите User ID пользователя, которому нужно выдать премиум:"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_remove_premium")
async def admin_remove_premium(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_user_id_remove)
    await callback.message.answer(
        "Введите User ID пользователя, у которого нужно снять премиум:"
    )
    await callback.answer()


@router.message(AdminStates.waiting_user_id_give)
async def process_give_premium(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно отправить числовой User ID.")
        return

    async with get_session() as session:
        stmt = select(User).where(User.telegram_user_id == target_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(
                "Проблема с выдачей премиума: пользователь не найден. "
                "Пусть сначала запустит бота командой /start❌"
            )
        else:
            if not user.is_premium:
                user.is_premium = True
                user.premium_since = datetime.now(ZoneInfo(settings.moscow_tz))
                await session.commit()
            nick = f"@{user.username}" if user.username else str(user.telegram_user_id)
            await message.answer(f"Успешно выдан премиум пользователю: {nick}✅")

    await state.clear()
    await message.answer(
        "Готово.",
        reply_markup=reply_main_keyboard(is_admin=True),
    )


@router.message(AdminStates.waiting_user_id_remove)
async def process_remove_premium(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно отправить числовой User ID.")
        return

    async with get_session() as session:
        stmt = select(User).where(User.telegram_user_id == target_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_premium:
            await message.answer(
                "Снятие не завершено. Возможно, пользователь не зарегистрирован "
                "в боте или у него не было премиума❌"
            )
        else:
            user.is_premium = False
            user.premium_since = None
            await session.commit()
            nick = f"@{user.username}" if user.username else str(user.telegram_user_id)
            await message.answer(
                f"Снятие премиума было успешно закончено✅\nПользователь: {nick}"
            )

    await state.clear()
    await message.answer(
        "Готово.",
        reply_markup=reply_main_keyboard(is_admin=True),
    )
