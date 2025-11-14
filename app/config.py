# app/config.py
import os
from dataclasses import dataclass


@dataclass
class Settings:
    bot_token: str
    openai_api_key: str
    openai_model: str
    database_url: str
    admin_id: int
    webhook_base_url: str
    webhook_path: str
    daily_limit: int
    moscow_tz: str = "Europe/Moscow"

    @classmethod
    def from_env(cls) -> "Settings":
        bot_token = os.getenv("BOT_TOKEN")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        database_url = os.getenv("DATABASE_URL")
        admin_id_raw = os.getenv("ADMIN_ID")
        webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "")
        webhook_path = os.getenv("WEBHOOK_PATH", "/webhook-gdz-iluxa")
        openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        daily_limit = int(os.getenv("DAILY_LIMIT", "15"))

        if not bot_token:
            raise RuntimeError("BOT_TOKEN is not set")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        if not database_url:
            raise RuntimeError("DATABASE_URL is not set")
        if not admin_id_raw:
            raise RuntimeError("ADMIN_ID is not set")

        if not database_url.startswith("postgresql+asyncpg://"):
            raise RuntimeError(
                "DATABASE_URL must start with 'postgresql+asyncpg://'"
            )

        return cls(
            bot_token=bot_token,
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            database_url=database_url,
            admin_id=int(admin_id_raw),
            webhook_base_url=webhook_base_url,
            webhook_path=webhook_path,
            daily_limit=daily_limit,
        )


settings = Settings.from_env()
