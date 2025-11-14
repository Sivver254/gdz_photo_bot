# app/handlers/admin.py
from __future__ import annotations

from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from app.config import settings
from app.db.models import User
from app.db.session import async_session_maker
from app.keyboards import inline_admin_panel_keyboard

router = Router(name="admin")


def _is_admin(user_id: int) -> bool:
    return user_id == settings.admin_id


@router.message(F.text == "Админ-Панель💎")
async def open_admin_panel(message: Message) -> None:
    """Открытие админ-панели по кнопке на reply-клавиатуре."""
    if not message.from_user:
        return

    if not _is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-панели❗")
        return

    await message.answer(
        "Админ-Панель, функционал полный снизу🔥",
        reply_markup=inline_admin_panel_keyboard(),
    )


@router.callback_query(F.data == "admin_give_premium")
async def admin_give_premium(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return

    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.message.answer("Введите User ID пользователя, которому выдать премиум:")
    await callback.answer()


@router.message(F.text.regexp(r"^\d+$"))
async def process_admin_user_id(message: Message) -> None:
    """
    Очень простой вариант:
    - если последнее сообщение в чате было 'Введите User ID…' и пишет админ —
      считаем, что он сейчас вводит ID и выдаём/снимаем премиум через отдельные команды.
    Чтобы не усложнять FSM, делаем две команды:
    /give_premium <user_id>
    /remove_premium <user_id>
    Но по ТЗ у тебя отдельные кнопки, так что лучше отдельные хэндлеры ниже.
    """
    # НИЧЕГО не делаем здесь, чтобы не ломать обычные числа от юзеров.
    # Админ команды делаем явно через callback'и ниже.
    pass


# === ВЫДАТЬ ПРЕМИУМ ПО CALLBACK С ВВОДОМ ID ===

_pending_action: dict[int, str] = {}  # admin_id -> "give" / "remove"


@router.callback_query(F.data == "admin_give_premium")
async def cb_start_give_premium(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    admin_id = callback.from_user.id
    if not _is_admin(admin_id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    _pending_action[admin_id] = "give"
    await callback.message.answer("Введите числовой User ID пользователя, которому выдать премиум:")
    await callback.answer()


@router.callback_query(F.data == "admin_remove_premium")
async def cb_start_remove_premium(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    admin_id = callback.from_user.id
    if not _is_admin(admin_id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    _pending_action[admin_id] = "remove"
    await callback.message.answer("Введите числовой User ID пользователя, у которого снять премиум:")
    await callback.answer()


@router.message(F.text.regexp(r"^\d+$"))
async def cb_process_premium_change(message: Message) -> None:
    """
    Обрабатываем ввод числового user_id, если до этого админ нажал одну из кнопок.
    """
    if not message.from_user:
        return
    admin_id = message.from_user.id
    if not _is_admin(admin_id):
        return

    action = _pending_action.get(admin_id)
    if not action:
        # Это просто число, не связанное с админ-действием
        return

    try:
        target_tg_id = int(message.text)
    except ValueError:
        await message.answer("Нужно отправить именно числовой User ID.")
        return

    async with async_session_maker() as session:
        result = await session.execute(
            User.__table__.select().where(User.telegram_user_id == target_tg_id)
        )
        row = result.first()

        if not row:
            await message.answer(
                "Проблема с пользователем: он не зарегистрирован в боте или произошла ошибка. "
                "Попроси его сначала написать боту /start❌"
            )
            _pending_action.pop(admin_id, None)
            return

        user = User(**row._mapping)

        if action == "give":
            user.is_premium = True
            user.premium_since = datetime.now(settings.tz)
            await session.merge(user)
            await session.commit()
            await message.answer(
                f"Успешно выдан премиум пользователю с ID {target_tg_id}✅"
            )
        elif action == "remove":
            user.is_premium = False
            user.premium_since = None
            await session.merge(user)
            await session.commit()
            await message.answer("Снятие премиума было успешно закончено✅")

    _pending_action.pop(admin_id, None)
