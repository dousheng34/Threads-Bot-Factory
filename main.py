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
    import os
    port = int(os.getenv("PORT", "8000"))
    if port != 8000:
        port = 8000
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def run_nextjs():
    import os
    if not os.path.exists("package.json"):
        logger.info("package.json not found. Skipping Next.js startup.")
        return
    
    port = os.getenv("PORT", "3000")
    if port == "8000":
        port = "3000"
        
    logger.info(f"Starting Next.js on port {port}...")
    try:
        process = await asyncio.create_subprocess_shell(
            f"npm run start -- -p {port}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        async def log_stream(stream, prefix):
            while True:
                line = await stream.readline()
                if not line:
                    break
                logger.info(f"[{prefix}] {line.decode().strip()}")
                
        await asyncio.gather(
            log_stream(process.stdout, "nextjs-out"),
            log_stream(process.stderr, "nextjs-err")
        )
    except Exception as e:
        logger.error(f"Failed to start Next.js: {e}")


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

    # Run webapp, bot, and Next.js concurrently
    await asyncio.gather(
        run_webapp(),
        run_bot(),
        run_nextjs(),
    )


if __name__ == "__main__":
    asyncio.run(main())

