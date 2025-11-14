# app/main.py

import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.config import settings
from app.db.session import init_db
from app.handlers import start, menu, photo, profile, admin
from app.keyboards import reply_main_keyboard  # noqa: F401  (чтобы модуль подхватился)


logger = logging.getLogger(__name__)


def create_dispatcher(bot: Bot) -> Dispatcher:
    """
    Собираем все роутеры бота в один Dispatcher.
    """
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(photo.router)
    dp.include_router(profile.router)
    dp.include_router(admin.router)

    return dp


async def on_startup(app: web.Application) -> None:
    """
    Вызывается при старте сервиса на Render.
    Тут:
    1) создаём/мигрируем БД
    2) ставим вебхук
    """
    bot: Bot = app["bot"]

    # 1. Инициализация БД (create_all + telegram_file_id)
    await init_db()

    # 2. Установка вебхука
    await bot.set_webhook(settings.webhook_url)
    logger.info("Webhook set to %s", settings.webhook_url)


async def on_shutdown(app: web.Application) -> None:
    """
    Аккуратное выключение бота.
    """
    bot: Bot = app["bot"]
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("Bot shutdown completed")


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Создаём бота
    bot = Bot(token=settings.bot_token, parse_mode="HTML")

    # Создаём диспетчер и подключаем хендлеры
    dp = create_dispatcher(bot)

    # Aiohttp-приложение для вебхука
    app = web.Application()
    app["bot"] = bot

    # Регистрируем обработчик вебхука по пути из настроек
    # Например: /webhook-gdz-iluxa
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    ).register(app, path=settings.webhook_path)

    # Подключаем внутренние хуки aiogram (startup/shutdown и т.д.)
    setup_application(app, dp, bot=bot)

    # Хуки старта/выключения для aiohttp
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Порт для Render — из переменной окружения PORT
    port = int(os.environ.get("PORT", 10000))

    logger.info("Starting web app on port %s", port)
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
