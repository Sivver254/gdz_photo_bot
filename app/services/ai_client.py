# app/services/ai_client.py
import asyncio
import base64
from typing import Optional

from openai import OpenAI

from app.config import settings

# Инициализируем новый OpenAI-клиент
client = OpenAI(api_key=settings.openai_api_key)

# Системная роль ИИ (чуть укороченная, но по сути та же)
SYSTEM_PROMPT = (
    "Ты — senior гуру образования России. Ты идеально знаешь школьные и "
    "колледж-программы РФ и аккуратно, по шагам решаешь задания по всем "
    "основным предметам. Отвечай чётко по заданию, без лишней воды."
)


async def call_openai_vision(
    image_bytes: bytes,
    caption: Optional[str],
    is_premium: bool,
) -> str:
    """
    Вызов GPT c поддержкой image + text через новый openai-клиент.
    Мы кодируем картинку в base64 и шлём как data:image/jpeg;base64,...
    Внешних запросов, asyncio.run и proxies — НЕТ.
    """

    # 1. base64 от картинки
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    # 2. Формируем промпт пользователя
    caption_part = caption.strip() if caption else ""
    user_text = (
        "Реши задание по фотографии. Если в подписи к фото есть указание "
        "какие номера решать или как отвечать — строго следуй этому.\n\n"
    )
    if caption_part:
        user_text += f"Подпись к фото: {caption_part}\n\n"

    user_text += (
        "Дай только решение/ответ без лишних пояснений. Если задание из "
        "языка, истории и т.п. — можешь кратко пояснить, но всё равно главное "
        "— сам ответ."
    )

    # 3. Сообщения для модели (vision через image_url data:)
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": SYSTEM_PROMPT}],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64_image}",
                    },
                },
            ],
        },
    ]

    max_tokens = 1200 if is_premium else 500

    def _call_sync() -> str:
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()

    # 4. Вызываем sync-клиент в отдельном потоке, чтобы не ломать event loop
    return await asyncio.to_thread(_call_sync)
