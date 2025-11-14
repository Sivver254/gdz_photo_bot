# app/handlers/photo.py
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
    PhotoSize,
)
from sqlalchemy import select

from app.config import settings
from app.db.session import get_session
from app.db.models import Task
from app.services.ai_client import call_openai_vision
from app.services.image_renderer import render_solution_image
from app.services.limits import (
    get_or_create_user,
    check_and_increment_daily_usage,
    DailyLimitExceeded,
)
from app.keyboards import inline_task_text_keyboard

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
    """Обработчик фото: качаем, шлём в OpenAI, рендерим решение."""

    if not message.from_user:
        return

    # Статус-сообщение, чтобы пользователь видел, что что-то происходит
    status = await message.answer("Фотку получил, думаю… 🤔")

    now_msk = datetime.now(ZoneInfo(settings.moscow_tz))

    # ===== 1. Пользователь + лимит =====
    async with get_session() as session:
        user = await get_or_create_user(
            session=session,
            tg_user_id=message.from_user.id,
            username=message.from_user.username,
            now_moscow=now_msk,
        )

        try:
            await check_and_increment_daily_usage(
                session=session,
                user=user,
                now_moscow=now_msk,
                daily_limit=settings.daily_limit,
            )
        except DailyLimitExceeded:
            await status.edit_text(
                "❌ Лимит на день исчерпан, дабы поддерживать функционал бота "
                "и избегать ошибок.\nПриходите через 12 часов ⏳"
            )
            return

    # ===== 2. Качаем фото =====
    try:
        buf = BytesIO()
        largest: PhotoSize = message.photo[-1]  # самое большое
        await message.bot.download(largest, buf)
        image_bytes = buf.getvalue()
    except Exception as e:
        await status.edit_text("❌ Не смог скачать фото. Попробуй ещё раз.")
        print("DOWNLOAD ERROR:", repr(e))
        return

    # ===== 3. Зовём OpenAI =====
    await status.edit_text("Анализирую изображение 📊…")

    try:
        answer = await call_openai_vision(
            image_bytes=image_bytes,
            caption=message.caption,
            is_premium=user.is_premium,
        )
    except RuntimeError as e:
        # Наши осознанные OPENAI_* ошибки
        await status.edit_text(
            "❌ Ошибка при работе с OpenAI.\n"
            f"{e}\n\n"
            "Это проблема конфигурации (ключ/модель/лимиты). "
            "После исправления всё заработает."
        )
        print("VISION ERROR:", repr(e))
        return
    except Exception as e:
        await status.edit_text(
            "❌ Неизвестная ошибка при анализе фото. Попробуй позже."
        )
        print("VISION UNKNOWN ERROR:", repr(e))
        return

    # ===== 4. Рендерим картинку с решением =====
    await status.edit_text("Создаю готовое решение 🧠🖼")

    try:
        result_image = render_solution_image(answer)
        file = BufferedInputFile(result_image, filename="solution.png")
    except Exception as e:
        await status.edit_text("❌ Ошибка при рендере изображения.")
        print("RENDER ERROR:", repr(e))
        return

    # ===== 5. Сохраняем задачу в БД =====
    async with get_session() as session:
        task = Task(
            user_id=user.id,
            created_at=now_msk,
            is_premium=user.is_premium,
            telegram_file_id=largest.file_id,
            answer_text=answer,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        task_id = task.id

    # ===== 6. Отправляем результат =====
    try:
        await status.delete()
    except Exception:
        pass

    await message.answer_photo(
        photo=file,
        caption="Готово!👇",
        reply_markup=inline_task_text_keyboard(task_id),
    )


@router.callback_query(F.data.startswith("task_text:"))
async def task_text(callback: CallbackQuery):
    """Отдаём текстовое решение по нажатию кнопки под картинкой."""
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
