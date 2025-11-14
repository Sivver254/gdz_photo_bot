# app/services/ai_client.py
import asyncio
import base64
from typing import Optional

from openai import (
    OpenAI,
    APIError,
    APIConnectionError,
    RateLimitError,
    AuthenticationError,
)

from app.config import settings

# Клиент OpenAI, ключ берём из настроек
client = OpenAI(api_key=settings.openai_api_key)

# Системная роль ИИ
SYSTEM_PROMPT = (
    "Ты — senior гуру образования России. Ты идеально знаешь школьные и "
    "колледж-программы РФ, аккуратно и по шагам решаешь школьные и "
    "колледж-задания. Отвечай чётко по условию, без лишней воды."
)


async def call_openai_vision(
    image_bytes: bytes,
    caption: Optional[str],
    is_premium: bool,
) -> str:
    """
    Вызов GPT с поддержкой картинок.
    Картинка шлётся в base64 через image_url (data:...).
    """

    # 1. Кодируем картинку
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    # 2. Текст пользователя
    caption_part = caption.strip() if caption else ""
    user_text = (
        "Реши задание по этой фотографии. Если в подписи указаны, какие номера "
        "решать или как именно отвечать — строго соблюдай это.\n\n"
    )
    if caption_part:
        user_text += f"Подпись к фото: {caption_part}\n\n"

    user_text += (
        "Дай в ответе само решение / ответы. Если нужно, можешь очень кратко "
        "пояснить, но без лишней воды."
    )

    # 3. Сообщения для модели
    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": SYSTEM_PROMPT},
            ],
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

    # 4. Синхронный вызов в отдельном потоке
    def _call_sync() -> str:
        try:
            resp = client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except AuthenticationError as e:
            # Неправильный / пустой ключ
            raise RuntimeError("OPENAI_AUTH_ERROR: проверь OPENAI_API_KEY") from e
        except RateLimitError as e:
            # Слишком много запросов / лимит тарифа
            raise RuntimeError("OPENAI_RATE_LIMIT: слишком много запросов") from e
        except APIConnectionError as e:
            # Проблемы с сетью / соединением
            raise RuntimeError("OPENAI_CONNECTION_ERROR: нет связи с OpenAI") from e
        except APIError as e:
            # Любая другая ошибка API (часто — закончился баланс)
            raise RuntimeError(f"OPENAI_API_ERROR: {e}") from e

    return await asyncio.to_thread(_call_sync)
