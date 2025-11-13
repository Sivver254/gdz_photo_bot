# app/config.py
import os
from dataclasses import dataclass


@dataclass
class Settings:
    bot_token: str
    openai_api_key: str
    database_url: str
    admin_id: int
    daily_limit: int = 15
    openai_model: str = "gpt-4.1-mini"
    moscow_tz: str = "Europe/Moscow"
    webhook_base_url: str | None = None  # например, https://gdz-photo-bot.onrender.com
    webhook_path: str = "/webhook"       # можешь переопределить через env


def load_settings() -> Settings:
    try:
        admin_id_raw = os.environ["ADMIN_ID"]
    except KeyError:
        raise RuntimeError("ENV ADMIN_ID is required")

    return Settings(
        bot_token=os.environ["BOT_TOKEN"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        database_url=os.environ["DATABASE_URL"],
        admin_id=int(admin_id_raw),
        daily_limit=int(os.getenv("DAILY_LIMIT", "15")),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        webhook_base_url=os.getenv("WEBHOOK_BASE_URL"),
        webhook_path=os.getenv("WEBHOOK_PATH", "/webhook"),
    )


settings = load_settings()