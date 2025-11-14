# app/keyboards.py
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def reply_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text="Главное меню🏠")]]
    if is_admin:
        rows.append([KeyboardButton(text="Админ-Панель💎")])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        selective=True,
    )


def inline_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать", callback_data="start_solve")],
            [InlineKeyboardButton(text="Главное меню🏠", callback_data="go_main_menu")],
        ]
    )


def inline_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать решать", callback_data="start_solve")],
            [
                InlineKeyboardButton(
                    text="Написать Илюшке",
                    url="https://t.me/flexchiko",
                )
            ],
            [InlineKeyboardButton(text="Правила", callback_data="menu_rules")],
            [InlineKeyboardButton(text="Премиум✨", callback_data="menu_premium")],
            [InlineKeyboardButton(text="Мой профиль👤", callback_data="menu_profile")],
        ]
    )


def inline_premium_contact_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Написать",
                    url="https://t.me/flexchiko",
                )
            ]
        ]
    )


def inline_task_text_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Получить в текстовом формате",
                    callback_data=f"task_text:{task_id}",
                )
            ]
        ]
    )


def inline_admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Выдать премиум🌟", callback_data="admin_give_premium"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Снять премиум🔥", callback_data="admin_remove_premium"
                )
            ],
        ]
    )
