import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database, Account

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

db = Database()
scheduler = AsyncIOScheduler(timezone="UTC")

async def post_for_account(account: Account):
    """Generate and post content for a single account."""
    try:
        from ai_post_generator import generate_post
        from threads_client import ThreadsClient  # your existing client

        logger.info(f"[{account.username}] Generating post...")
        topic = account.ai_topic or "general lifestyle"
        content = await generate_post(topic)

        client = ThreadsClient(account.username, account.password, account.proxy_url)
        await client.login()
        post_id = await client.post(content)

        await db.log_action(account.id, "post", f"Posted: {post_id}")
        logger.info(f"[{account.username}] Posted successfully: {post_id}")
    except Exception as e:
        logger.error(f"[{account.username}] Post error: {e}")
        await db.log_action(account.id, "error", str(e))

async def comment_for_account(account: Account):
    """Auto-comment on trending posts."""
    try:
        from ai_handlers import generate_comment
        from threads_client import ThreadsClient

        logger.info(f"[{account.username}] Auto-commenting...")
        client = ThreadsClient(account.username, account.password, account.proxy_url)
        await client.login()

        trending = await client.get_trending_posts(limit=5)
        for post in trending[:2]:
            comment = await generate_comment(post.get("text", ""))
            await client.comment(post["id"], comment)
            await asyncio.sleep(10)

        await db.log_action(account.id, "comment", f"Commented on {len(trending[:2])} posts")
    except Exception as e:
        logger.error(f"[{account.username}] Comment error: {e}")

async def run_all_accounts(task: str):
    """Run a task for all active accounts."""
    accounts = await db.get_all_accounts()
    active = [a for a in accounts if a.is_active]
    logger.info(f"Running '{task}' for {len(active)} active accounts")

    tasks = []
    for account in active:
        if task == "post":
            tasks.append(post_for_account(account))
        elif task == "comment":
            tasks.append(comment_for_account(account))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

async def morning_post():
    logger.info("=== Morning post schedule ===")
    await run_all_accounts("post")

async def noon_post():
    logger.info("=== Noon post schedule ===")
    await run_all_accounts("post")

async def evening_post():
    logger.info("=== Evening post schedule ===")
    await run_all_accounts("post")

async def night_post():
    logger.info("=== Night post schedule ===")
    await run_all_accounts("post")

async def auto_comment():
    logger.info("=== Auto comment schedule ===")
    await run_all_accounts("comment")

def start_scheduler(schedule_config: dict = None):
    """Start the scheduler with given config."""
    config = schedule_config or {
        "morning": True,
        "noon": True,
        "evening": False,
        "night": False,
        "ai_comments": True,
        "auto_likes": False,
    }

    if config.get("morning"):
        scheduler.add_job(morning_post, "cron", hour=9, minute=0, id="morning_post", replace_existing=True)
    if config.get("noon"):
        scheduler.add_job(noon_post, "cron", hour=13, minute=0, id="noon_post", replace_existing=True)
    if config.get("evening"):
        scheduler.add_job(evening_post, "cron", hour=17, minute=0, id="evening_post", replace_existing=True)
    if config.get("night"):
        scheduler.add_job(night_post, "cron", hour=21, minute=0, id="night_post", replace_existing=True)
    if config.get("ai_comments"):
        scheduler.add_job(auto_comment, "cron", hour="*/3", minute=30, id="auto_comment", replace_existing=True)

    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started!")

def update_schedule(config: dict):
    """Update scheduler jobs dynamically."""
    job_map = {
        "morning": (morning_post, "cron", {"hour": 9}),
        "noon": (noon_post, "cron", {"hour": 13}),
        "evening": (evening_post, "cron", {"hour": 17}),
        "night": (night_post, "cron", {"hour": 21}),
        "ai_comments": (auto_comment, "cron", {"hour": "*/3", "minute": 30}),
    }
    for key, (func, trigger, kwargs) in job_map.items():
        job_id = f"{key}_job"
        if config.get(key):
            scheduler.add_job(func, trigger, id=job_id, replace_existing=True, **kwargs)
        else:
            try:
                scheduler.remove_job(job_id)
            except Exception:
                pass
    logger.info(f"Schedule updated: {config}")
