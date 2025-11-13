# app/services/ai_client.py
import asyncio
import base64
from typing import Optional

from openai import OpenAI, APIError, RateLimitError

from app.config import settings

client = OpenAI(api_key=settings.openai_api_key)


SYSTEM_PROMPT_BASE = (
    "Ты — senior гуру образования России. Ты идеально знаешь школьные и "
    "колледж-программы РФ и решаешь задания по предметам: "
    "Русский язык, Литература, Иностранный язык (английский, немецкий, "
    "французский, испанский, итальянский, китайский, японский, арабский, "
    "турецкий, корейский), Математика, Алгебра, Геометрия, Информатика, "
    "История России, Всеобщая история, Обществознание, География, Биология, "
    "Физика, Химия, Астрономия, Экономика, Право, Экология, Психология, "
    "Риторика, Культура речи, Технология, Музыка, Изобразительное искусство, "
    "Физическая культура, ОБЖ, Индивидуальный проект, Основы философии, "
    "Правоведение, Экономика организации, Документационное обеспечение управления, "
    "Основы менеджмента, Маркетинг, Психология общения, Деловая этика, "
    "Производственная практика, Профессиональные модули, Проектная деятельность.\n\n"
    "Твоя задача — аккуратно, по шагам и без лишней воды решать задания "
    "и давать понятные ответы."
)

SYSTEM_PREMIUM_SUFFIX = (
    "\n\nСейчас премиум-режим: делай ответы максимально качественными, аккуратно "
    "поясняй ход решения, при необходимости кратко поясняй теорию. "
    "Если задание не полностью читается, аккуратно восстанавливай смысл по контексту "
    "и честно указывай, где есть предположения."
)

SYSTEM_NORMAL_SUFFIX = (
    "\n\nСейчас обычный режим: отвечай достаточно кратко, без лишней воды, "
    "но так, чтобы можно было понять решение."
)


async def call_openai_vision(
    image_bytes: bytes,
    caption: Optional[str],
    is_premium: bool,
) -> str:
    """
    Возвращает текстовый ответ ИИ (решение).
    """
    system_prompt = SYSTEM_PROMPT_BASE + (SYSTEM_PREMIUM_SUFFIX if is_premium else SYSTEM_NORMAL_SUFFIX)

    user_text = (
        "На изображении сфотографировано задание. "
        "Сначала пойми, по какому это предмету и что именно требуется сделать. "
        "Затем реши задание. Если пользователь просит решать только отдельные номера, "
        "делай только их. "
        "Ответ давай по шагам и аккуратно."
    )
    if caption:
        user_text += f"\n\nПодпись пользователя к фото: «{caption}»."

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": settings.openai_model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "input_image",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}"
                        },
                    },
                ],
            },
        ],
        "temperature": 0.2 if not is_premium else 0.3,
        "max_tokens": 1200 if is_premium else 700,
    }

    loop = asyncio.get_running_loop()

    async def _call_with_retries() -> str:
        for attempt in range(3):
            try:
                resp = await loop.run_in_executor(
                    None, lambda: client.chat.completions.create(**payload)
                )
                return resp.choices[0].message.content.strip()
            except RateLimitError:
                await asyncio.sleep(2 ** attempt)
            except APIError as e:
                if e.status_code and e.status_code >= 500:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        raise RuntimeError("Не удалось получить ответ от OpenAI после нескольких попыток")

    return await _call_with_retries()