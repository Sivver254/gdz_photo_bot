# app/services/image_renderer.py
from __future__ import annotations

from io import BytesIO
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


IMAGE_WIDTH = 1200
PADDING = 60
BG_COLOR = (15, 15, 15)       # тёмный фон
TEXT_COLOR = (240, 240, 240)  # почти белый текст
FONT_SIZE = 42
MAX_CHARS_PER_LINE = 60       # примерная ширина строки


def _get_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    Пытаемся взять нормальный TTF-шрифт.
    Если на сервере его нет – берём дефолтный.
    """
    try:
        return ImageFont.truetype("DejaVuSans.ttf", FONT_SIZE)
    except Exception:
        return ImageFont.load_default()


def _prepare_lines(text: str) -> list[str]:
    """Разбиваем текст на аккуратные строки."""
    font = _get_font()
    lines: list[str] = []

    for paragraph in text.split("\n"):
        paragraph = paragraph.rstrip()
        if not paragraph:
            lines.append("")
            continue
        wrapped = wrap(paragraph, width=MAX_CHARS_PER_LINE)
        if not wrapped:
            lines.append("")
        else:
            lines.extend(wrapped)

    if not lines:
        lines = ["(пусто)"]

    return lines, font


def render_solution_image(text: str) -> bytes:
    """
    Рендерит текст решения в PNG-картинку и возвращает байты.
    Именно ЭТУ функцию импортирует handler фото.
    """
    lines, font = _prepare_lines(text)

    # высота строки
    bbox = font.getbbox("Ay")
    line_height = bbox[3] - bbox[1] + 8

    img_height = PADDING * 2 + line_height * len(lines)

    img = Image.new("RGB", (IMAGE_WIDTH, img_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = PADDING
    for line in lines:
        draw.text((PADDING, y), line, font=font, fill=TEXT_COLOR)
        y += line_height

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# На всякий случай алиас – если где-то будешь импортить другое имя
def render_text_to_image(text: str) -> bytes:
    return render_solution_image(text)
