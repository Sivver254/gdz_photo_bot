# Telegram-бот «ГДЗ по фото»

Бот принимает фото задания, решает его с помощью OpenAI (vision) и
возвращает решение картинкой + по запросу текстом.

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt