# app/main.py

import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.config import settings
from app.db.session import init_db
from app.handlers import start, menu, photo, profile, admin


# ===== Настройка логов =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ===== Webhook =====
WEBHOOK_PATH = "/webhook-gdz-iluxa"


def get_webhook_url() -> str:
    """
    Адрес вебхука.
    На Render автоматически доступна переменная RENDER_EXTERNAL_URL.
    Если её нет — можно задать BASE_WEBHOOK_URL в settings / .env.
    """
    base_url = os.getenv("RENDER_EXTERNAL_URL") or getattr(
        settings, "base_webhook_url", ""
    )
    base_url = base_url.rstrip("/")
    return f"{base_url}{WEBHOOK_PATH}"


# ===== Aiohttp healthcheck =====
async def healthcheck(request: web.Request) -> web.Response:
    return web.Response(text="OK")


# ===== Стартовые хуки dp =====
async def on_startup(bot: Bot) -> None:
    await init_db()
    webhook_url = get_webhook_url()
    logger.info("Setting webhook to: %s", webhook_url)
    await bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True,
    )
    logger.info("Webhook set")


async def on_shutdown(bot: Bot) -> None:
    logger.info("Shutting down bot...")
    await bot.delete_webhook(drop_pending_updates=False)
    logger.info("Webhook deleted")


# ===== Основной запуск =====
async def main() -> None:
    # ВАЖНО: parse_mode задаём через DefaultBotProperties, а не параметром Bot(...)
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Регистрируем хуки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Подключаем роутеры
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(photo.router)
    dp.include_router(profile.router)
    dp.include_router(admin.router)

    # Aiohttp-приложение для вебхука
    app = web.Application()
    app.router.add_get("/", healthcheck)
    app.router.add_get("/health", healthcheck)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info("Webhook app is running on http://0.0.0.0:%s", port)
    logger.info("Press CTRL+C to stop")

    # Живём вечно
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
