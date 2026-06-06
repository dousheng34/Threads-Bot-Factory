"""
main.py — Unified entrypoint
Runs FastAPI webapp + Telegram bot concurrently
"""
import asyncio
import logging
import uvicorn
from webapp import app
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


import os

async def run_webapp():
    port = int(os.getenv("PORT", "8000"))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def run_bot():
    from bot import dp, bot
    import os
    if os.getenv("WEBAPP_URL"):
        logger.info("WEBAPP_URL is configured. Telegram bot will operate in WEBHOOK mode. Skipping polling.")
        return
    logger.info("Starting Telegram bot in POLLING mode...")
    await dp.start_polling(bot)


async def main():
    import database as db
    await db.init_db()
    logger.info("Database initialized")
    
    start_scheduler()
    logger.info("Scheduler started")

    # Run webapp and bot concurrently
    await asyncio.gather(
        run_webapp(),
        run_bot(),
    )


if __name__ == "__main__":
    asyncio.run(main())
