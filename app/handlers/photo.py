# app/handlers/photo.py
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import Message, PhotoSize, CallbackQuery
from sqlalchemy import select

from app.config import settings
from app.db.models import Task
from app.db.session import get_session
from app.keyboards import inline_task_text_keyboard
from app.services.ai_client import call_openai_vision
from app.services.image_renderer import render_solution_image
from app.services.limits import (
    get_or_create_user,
    check_and_increment_daily_usage,
    DailyLimitExceeded,
)

router = Router()


@router.callback_query(F.data == "start_solve")
async def start_solve(callback: CallbackQuery):
    await callback.message.answer(
        "Отправь мне фото задания и я его обязательно решу, "
        "за правильность ответа не отвечаю 🐒"
    )
    await callback.answer()


@router.message(F.photo)
async def handle_photo(message: Message):
    if not message.from_user:
        return

    moscow_now = datetime.now(ZoneInfo(settings.moscow_tz))

    async with get_session() as session:
        user = await get_or_create_user(
            session=session,
            tg_user_id=message.from_user.id,
            username=message.from_user.username,
            now_moscow=moscow_now,
        )

        try:
            await check_and_increment_daily_usage(
                session=session,
                user=user,
                now_moscow=moscow_now,
                daily_limit=settings.daily_limit,
            )
        except DailyLimitExceeded:
            await message.answer(
                "Лимит на день исчерпан, дабы поддерживать функционал бота "
                "и избегать ошибок ❗\nПриходите через 12 часов⏳"
            )
            return

    largest_photo: PhotoSize = message.photo[-1]
    buf = BytesIO()
    await largest_photo.download(destination=buf)
    image_bytes = buf.getvalue()

    status = await message.answer("Анализирую фотографию📈")

    try:
        answer_text = await call_openai_vision(
            image_bytes=image_bytes,
            caption=message.caption,
            is_premium=user.is_premium,
        )

        await status.edit_text("Создаю решение🎉")
        await status.edit_text("Пишу результат ⏳")

        image_answer_bytes = render_solution_image(answer_text)

        async with get_session() as session:
            task = Task(
                user_id=user.id,
                created_at=moscow_now,
                is_premium=user.is_premium,
                telegram_file_id=largest_photo.file_id,
                answer_text=answer_text,
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            task_id = task.id

        await status.delete()
        await message.answer_photo(
            photo=image_answer_bytes,
            caption="Готово✅",
            reply_markup=inline_task_text_keyboard(task_id),
        )

    except Exception as e:
        try:
            await status.edit_text(
                "Произошла ошибка при обработке изображения. "
                "Попробуйте ещё раз позже."
            )
        except Exception:
            await message.answer(
                "Произошла ошибка при обработке изображения. "
                "Попробуйте ещё раз позже."
            )
        print("Error in handle_photo:", repr(e))


@router.callback_query(F.data.startswith("task_text:"))
async def task_text(callback: CallbackQuery):
    _, task_id_str = callback.data.split(":", 1)
    try:
        task_id = int(task_id_str)
    except ValueError:
        await callback.answer("Неверный ID задачи", show_alert=True)
        return

    async with get_session() as session:
        stmt = select(Task).where(Task.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

    if not task:
        await callback.answer("Решение не найдено", show_alert=True)
        return

    await callback.message.answer(task.answer_text)
    await callback.answer()
