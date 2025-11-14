# app/main.py
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)

from app.config import settings
from app.db.session import init_db
from app.handlers import start, menu, photo, profile, admin
from app.keyboards import reply_main_keyboard


async def on_startup(app: web.Application):
    await init_db()

    bot: Bot = app["bot"]

    if not settings.webhook_base_url:
        print("WARNING: WEBHOOK_BASE_URL is not set")
        return

    webhook_url = settings.webhook_base_url.rstrip("/") + settings.webhook_path
    await bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
    )
    print(f"Webhook set to: {webhook_url}")


async def on_shutdown(app: web.Application):
    bot: Bot = app["bot"]
    await bot.delete_webhook(drop_pending_updates=False)
    await bot.session.close()


async def healthcheck(request: web.Request) -> web.Response:
    return web.Response(text="OK")


def main():
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(photo.router)
    dp.include_router(profile.router)
    dp.include_router(admin.router)

    app = web.Application()
    app["bot"] = bot
    app["dispatcher"] = dp

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    ).register(app, path=settings.webhook_path)

    app.router.add_get("/", healthcheck)

    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    port = int(os.getenv("PORT", "10000"))
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
