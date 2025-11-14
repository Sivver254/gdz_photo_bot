# app/handlers/photo.py
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import (
    Message,
    PhotoSize,
    CallbackQuery,
    BufferedInputFile,
)
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
    """
    Основной обработчик фото.
    Тут были две проблемы:
    1) в aiogram 3 у PhotoSize нет .download()
    2) answer_photo нужно отдавать InputFile, а не просто bytes
    Обе исправлены в этом варианте.
    """
    if not message.from_user:
        return

    moscow_now = datetime.now(ZoneInfo(settings.moscow_tz))

    # 1. Регистрируем/находим пользователя и проверяем лимит
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

    # 2. Скачиваем фото корректным способом для aiogram 3
    largest_photo: PhotoSize = message.photo[-1]

    buf = BytesIO()
    # В aiogram 3 скачиваем через bot.download(), а не через photo.download()
    await message.bot.download(largest_photo, buf)
    image_bytes = buf.getvalue()

    # 3. Статус-сообщение
    status = await message.answer("Анализирую фотографию📈")

    try:
        # 4. Вызываем OpenAI
        answer_text = await call_openai_vision(
            image_bytes=image_bytes,
            caption=message.caption,
            is_premium=user.is_premium,
        )

        await status.edit_text("Создаю решение🎉")
        await status.edit_text("Пишу результат ⏳")

        # 5. Рендерим картинку с решением
        image_answer_bytes = render_solution_image(answer_text)
        input_file = BufferedInputFile(
            image_answer_bytes,
            filename="solution.png",
        )

        # 6. Сохраняем задачу в БД
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

        # 7. Отправляем результат
        try:
            await status.delete()
        except Exception:
            pass

        await message.answer_photo(
            photo=input_file,
            caption="Готово✅",
            reply_markup=inline_task_text_keyboard(task_id),
        )

    except Exception as e:
        # Любая ошибка при обработке фото – пишем юзеру, лог не гробим
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
