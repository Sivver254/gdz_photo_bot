# app/services/image_renderer.py
from io import BytesIO
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

IMAGE_WIDTH = 1200
PADDING = 60
BG_COLOR = (15, 15, 15)
TEXT_COLOR = (240, 240, 240)
FONT_SIZE = 42
MAX_CHARS_PER_LINE = 60


def _get_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", FONT_SIZE)
    except Exception:
        return ImageFont.load_default()


def _split_lines(text: str) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.rstrip()
        if not paragraph:
            lines.append("")
            continue
        wrapped = wrap(paragraph, width=MAX_CHARS_PER_LINE)
        lines.extend(wrapped or [""])
    if not lines:
        lines = ["(пусто)"]
    return lines


def render_solution_image(text: str) -> bytes:
    font = _get_font()
    lines = _split_lines(text)
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


def render_text_to_image(text: str) -> bytes:
    return render_solution_image(text)
