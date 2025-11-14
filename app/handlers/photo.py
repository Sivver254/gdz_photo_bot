# app/handlers/photo.py
from __future__ import annotations

from io import BytesIO
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BufferedInputFile

from app.config import settings
from app.db.models import User, Task
from app.db.session import async_session_maker
from app.keyboards import inline_task_text_keyboard
from app.services.ai_client import call_openai_vision
from app.services.image_renderer import render_solution_image
from app.services.limits import DailyLimitExceeded, check_and_increment_daily_usage

router = Router(name="photo")


async def _get_or_create_user(telegram_user_id: int, username: str | None) -> User:
    """Достаём пользователя из БД или создаём нового."""
    async with async_session_maker() as session:
        user = await session.get(User, {"telegram_user_id": telegram_user_id})
        if user is None:
            user = User(
                telegram_user_id=telegram_user_id,
                username=username,
                first_seen_at=datetime.now(settings.tz),
                is_premium=False,
                premium_since=None,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
    return user


@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext) -> None:
    """
    Обрабатываем ЛЮБОЕ фото, без привязки к состоянию.
    Так у тебя не будет ситуации, когда бот молчит.
    """
    if not message.from_user:
        return

    user_tg_id = message.from_user.id
    username = message.from_user.username

    # 1. Достаём/создаём пользователя
    user = await _get_or_create_user(user_tg_id, username)

    # 2. Проверяем лимиты (для премиума лимитов нет)
    async with async_session_maker() as session:
        try:
            await check_and_increment_daily_usage(session, user)
        except DailyLimitExceeded:
            await message.answer(
                "Лимит на день исчерпан, дабы поддерживать функционал бота и избегать ошибок ❗\n"
                "Приходите через 12 часов⏳"
            )
            return

    # 3. Сообщение-статус
    status_msg = await message.answer("Анализирую фотографию📈")

    try:
        # 4. Скачиваем фото как байты
        largest_photo = message.photo[-1]
        buf = BytesIO()
        await message.bot.download(largest_photo, buf)
        image_bytes = buf.getvalue()

        # 5. Подготовка промпта для ИИ
        user_caption = message.caption or ""
        user_prompt = (
            "Ты — гуру образования России. Тебе прислали фото задания.\n"
            "Аккуратно распознай текст (включая рукописный), пойми, что нужно сделать, "
            "реши задание и оформи понятный ответ для школьника/студента.\n"
            "Если есть подпись к фото (например: 'реши только 1 и 3 номер'), учитывай её строго.\n"
            "Дай готовое решение без лишней воды.\n\n"
            f"Подпись пользователя к фото: {user_caption}"
        )

        # 6. Обновляем статус
        await status_msg.edit_text("Создаю решение🎉")

        # 7. Вызываем OpenAI (vision)
        solution_text = await call_openai_vision(
            image_bytes=image_bytes,
            user_prompt=user_prompt,
            is_premium=user.is_premium,
        )

        # 8. Ещё раз статус
        await status_msg.edit_text("Пишу результат ⏳")

        # 9. Рендерим картинку с ответом
        solution_image_bytes = await render_solution_image(solution_text)

        # 10. Сохраняем задачу в БД
        async with async_session_maker() as session:
            task = Task(
                user_id=user.id,
                created_at=datetime.now(settings.tz),
                is_premium=user.is_premium,
                telegram_file_id="",  # заполним после отправки фото
                answer_text=solution_text,
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)

        # 11. Отправляем фото-ответ
        photo_file = BufferedInputFile(solution_image_bytes, filename="solution.png")
        await status_msg.delete()

        sent_photo_msg = await message.answer_photo(
            photo=photo_file,
            caption="Готово✅",
            reply_markup=inline_task_text_keyboard(task.id),
        )

        # 12. Обновляем file_id в БД
        if sent_photo_msg.photo:
            new_file_id = sent_photo_msg.photo[-1].file_id
            async with async_session_maker() as session:
                db_task = await session.get(Task, task.id)
                if db_task:
                    db_task.telegram_file_id = new_file_id
                    await session.commit()

    except Exception as e:
        # На всякий случай ловим любые сбои, чтобы не было тишины
        try:
            await status_msg.edit_text(
                "Произошла ошибка при обработке изображения 😔\n"
                "Попробуйте ещё раз позже или отправьте другое фото."
            )
        except Exception:
            await message.answer(
                "Произошла ошибка при обработке изображения 😔\n"
                "Попробуйте ещё раз позже или отправьте другое фото."
            )
        # В логах Render ты увидишь подробную трассировку
        print("Error while processing photo:", repr(e))
