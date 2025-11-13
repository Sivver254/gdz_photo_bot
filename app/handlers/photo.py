# app/handlers/photo.py
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO

from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PhotoSize
from sqlalchemy import select

from app.config import settings
from app.db.models import User, Task
from app.db.session import get_session
from app.keyboards import inline_task_text_keyboard
from app.services.ai_client import call_openai_vision
from app.services.image_renderer import render_text_to_image
from app.services.limits import get_or_create_user, check_and_increment_daily_limit

router = Router()


class PhotoStates(StatesGroup):
    waiting_for_photo = State()


@router.callback_query(F.data == "start_solve")
async def start_solve(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PhotoStates.waiting_for_photo)
    await callback.message.answer(
        "Отправь мне фото задания и я его обязательно решу, за правильность ответа не отвечаю 🐒"
    )
    await callback.answer()


@router.message(PhotoStates.waiting_for_photo, F.photo)
async def handle_photo(message: Message, state: FSMContext):
    moscow_now = datetime.now(ZoneInfo(settings.moscow_tz))

    async with await get_session() as session:
        user = await get_or_create_user(
            session=session,
            tg_user_id=message.from_user.id,
            username=message.from_user.username,
            now_moscow=moscow_now,
        )

        allowed, used = await check_and_increment_daily_limit(
            session=session,
            user=user,
            now_moscow=moscow_now,
            daily_limit=settings.daily_limit,
        )

    if not allowed:
        await message.answer(
            "Лимит на день исчерпан, дабы поддерживать функционал бота и избегать ошибок ❗\n"
            "Приходите через 12 часов⏳"
        )
        return

    largest_photo: PhotoSize = message.photo[-1]

    buffer = BytesIO()
    await largest_photo.download(destination=buffer)
    image_bytes = buffer.getvalue()

    status = await message.answer("Анализирую фотографию📈")

    try:
        answer_text = await call_openai_vision(
            image_bytes=image_bytes,
            caption=message.caption,
            is_premium=user.is_premium,
        )

        await status.edit_text("Создаю решение🎉")
        await status.edit_text("Пишу результат ⏳")

        img_bytes = render_text_to_image(answer_text)

        async with await get_session() as session:
            task = Task(
                user_id=user.id,
                is_premium=user.is_premium,
                photo_file_id=largest_photo.file_id,
                answer_text=answer_text,
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            task_id = task.id

        await status.delete()

        await message.answer("Готово✅")

        await message.answer_photo(
            photo=img_bytes,
            caption="Вот твоё решение 👆",
            reply_markup=inline_task_text_keyboard(task_id),
        )

    except Exception:
        try:
            await status.edit_text(
                "Произошла ошибка при обработке изображения. Попробуйте ещё раз чуть позже."
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("task_text:"))
async def task_text(callback: CallbackQuery):
    _, task_id_str = callback.data.split(":", 1)
    try:
        task_id = int(task_id_str)
    except ValueError:
        await callback.answer("Ошибка ID задачи", show_alert=True)
        return

    async with await get_session() as session:
        stmt = select(Task).where(Task.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

    if not task:
        await callback.answer("Не нашёл решение для этой задачи", show_alert=True)
        return

    await callback.message.answer(task.answer_text)
    await callback.answer()