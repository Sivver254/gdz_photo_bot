# app/services/image_renderer.py
from io import BytesIO
import textwrap

from PIL import Image, ImageDraw, ImageFont


def render_text_to_image(answer_text: str) -> bytes:
    """
    Рендерит текст решения в PNG-картинку
    """
    width = 1200
    padding = 80
    background_color = (15, 15, 15)
    text_color = (240, 240, 240)
    heading_color = (255, 255, 255)

    title = "Результат\n(ГДЗ по фото)"
    wrapped_answer = _wrap_text(answer_text, max_chars=70)

    try:
        font_title = ImageFont.truetype("arial.ttf", 40)
        font_text = ImageFont.truetype("arial.ttf", 30)
    except OSError:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()

    temp_img = Image.new("RGB", (width, 1000), background_color)
    draw = ImageDraw.Draw(temp_img)

    title_bbox = draw.multiline_textbbox((0, 0), title, font=font_title, align="center")
    answer_bbox = draw.multiline_textbbox((0, 0), wrapped_answer, font=font_text)

    height = (
        padding * 2
        + (title_bbox[3] - title_bbox[1])
        + 40
        + (answer_bbox[3] - answer_bbox[1])
    )

    img = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(img)

    current_y = padding
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.multiline_text((title_x, current_y), title, font=font_title, fill=heading_color, align="center")

    current_y += (title_bbox[3] - title_bbox[1]) + 40

    draw.multiline_text(
        (padding, current_y),
        wrapped_answer,
        font=font_text,
        fill=text_color,
        align="left",
        spacing=8,
    )

    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output.read()


def _wrap_text(text: str, max_chars: int = 70) -> str:
    lines = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        lines.extend(textwrap.wrap(paragraph, width=max_chars))
    return "\n".join(lines)