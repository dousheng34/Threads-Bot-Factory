"""
Threads Bot Factory - Telegram Bot
"""
import asyncio, json, os, logging
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
from threads_api import publish_thread, process_spintax
from oauth import get_auth_url, pending_auth, start_oauth_server
import uuid

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = set(int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip())

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
scheduler = AsyncIOScheduler()

async def health_handler(request):
    return web.Response(text="OK", status=200)

async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/", health_handler)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Health check server started on port {port}")

async def main():
    await db.init_db()
    dp.include_router(router)
    await start_health_server()
    await start_oauth_server(5000)
    scheduler.start()
    logging.info("Threads Bot Factory started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
