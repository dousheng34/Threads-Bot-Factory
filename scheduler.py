import asyncio
import logging
import random
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import database as db

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")

async def post_for_account(account: dict):
    """Generate and post content for a single account."""
    try:
        from ai_post_generator import generate_post
        from meta_service import meta_service
        from whatsapp_service import whatsapp_service

        logger.info(f"[{account['username']}] Generating auto-post...")
        
        # Determine topic from settings or use general default
        import json
        settings_dict = {}
        try:
            settings_dict = json.loads(account.get("settings") or "{}")
        except Exception:
            pass
            
        topic = settings_dict.get("ai_topic") or "general lifestyle & tech"
        content = await generate_post(topic)

        success = False
        ext_id = None
        err_msg = None
        platform = account["platform"]

        if platform == "threads":
            res = await meta_service.publish_threads_post(
                threads_user_id=account["threads_user_id"],
                access_token=account["access_token"],
                text=content
            )
            success = res.get("success", False)
            ext_id = res.get("thread_id")
            err_msg = res.get("error")
            
        elif platform == "instagram":
            # Instagram requires media, let's supply a fallback placeholder image
            res = await meta_service.publish_instagram_post(
                threads_user_id=account["threads_user_id"],
                access_token=account["access_token"],
                caption=content,
                media_url="https://picsum.photos/800/800"
            )
            success = res.get("success", False)
            ext_id = res.get("post_id")
            err_msg = res.get("error")
            
        elif platform == "whatsapp":
            res = await whatsapp_service.send_whatsapp_message(
                phone_number_id=account["threads_user_id"],
                access_token=account["access_token"],
                recipient_phone=account["username"],
                message_text=content
            )
            success = res.get("success", False)
            ext_id = res.get("message_id")
            err_msg = res.get("error")

        status_str = "success" if success else "error"
        await db.log_post(
            account_id=account["id"],
            content=content,
            status=status_str,
            thread_id=ext_id,
            error=err_msg,
            user_id=account["user_id"]
        )

        if success:
            logger.info(f"[{account['username']}] Auto-posted successfully: {ext_id}")
        else:
            logger.error(f"[{account['username']}] Auto-post failed: {err_msg}")

    except Exception as e:
        logger.error(f"[{account.get('username', 'Unknown')}] Post error: {e}")


async def comment_for_account(account: dict):
    """Auto-comment on trending posts for Threads/Instagram accounts."""
    try:
        from ai_handlers import generate_comment
        from meta_service import meta_service

        platform = account["platform"]
        if platform not in ("threads", "instagram"):
            return # WhatsApp does not support public comment sections

        logger.info(f"[{account['username']}] Running auto-commenting...")
        
        # In a real environment, we fetch trending posts or feed replies
        # For prototype, we simulate comments on simulated recent items
        comments_made = 0
        simulated_posts = ["threads_feed_1", "threads_feed_2"]
        
        for post_id in simulated_posts:
            comment_text = await generate_comment("Welcome to the future of AI automation platforms!")
            success = False
            
            if platform == "threads":
                res = await meta_service.reply_to_threads_comment(
                    access_token=account["access_token"],
                    parent_id=post_id,
                    reply_text=comment_text
                )
                success = res.get("success", False)
            elif platform == "instagram":
                res = await meta_service.reply_to_instagram_comment(
                    access_token=account["access_token"],
                    comment_id=post_id,
                    reply_text=comment_text
                )
                success = res.get("success", False)

            if success:
                comments_made += 1
            await asyncio.sleep(2)

        logger.info(f"[{account['username']}] Commented on {comments_made} posts.")

    except Exception as e:
        logger.error(f"[{account.get('username', 'Unknown')}] Auto-comment error: {e}")


async def run_all_accounts(task: str):
    """Run a task for all active accounts."""
    accounts = await db.get_social_accounts(status="active")
    logger.info(f"Running '{task}' scheduler task for {len(accounts)} active accounts")

    tasks = []
    for account in accounts:
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


async def collect_weekly_analytics():
    """Collect analytics snapshots for all active accounts to track growth."""
    logger.info("=== Collecting weekly analytics snapshots ===")
    
    accounts = await db.get_social_accounts(status="active")
    day = datetime.now().strftime("%Y-%m-%d")
    
    for acc in accounts:
        try:
            # Simulate organic growth (+1-5% followers, random impressions/clicks)
            current_followers = acc.get("followers_count") or 0
            growth = int(current_followers * random.uniform(0.01, 0.05)) if current_followers > 0 else random.randint(5, 20)
            new_followers = current_followers + growth
            
            # Update the account followers count in social_accounts table
            await db.update_social_account(acc["id"], followers_count=new_followers)
            
            # Generate metrics
            impressions = random.randint(100, 5000)
            clicks = random.randint(10, 500)
            engagement = random.randint(20, 1000)
            
            await db.add_analytics_snapshot(
                social_account_id=acc["id"],
                snapshot_date=day,
                followers=new_followers,
                impressions=impressions,
                engagement=engagement,
                clicks=clicks
            )
            logger.info(f"[{acc['username']}] Analytics snapshot created for {day} (Followers: {new_followers})")
        except Exception as e:
            logger.error(f"[{acc.get('username')}] Failed to log analytics: {e}")


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

    # Weekly analytics snapshots collection job (run every Sunday at 00:00)
    scheduler.add_job(collect_weekly_analytics, "cron", day_of_week="sun", hour=0, minute=0, id="weekly_analytics", replace_existing=True)

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
