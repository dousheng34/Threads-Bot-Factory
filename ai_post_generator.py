"""
AI Post Generator — bulk-generate posts on a topic and queue them
into the existing scheduled_posts table.
"""
import os, asyncio, random, logging
import aiosqlite
from datetime import datetime, timedelta, timezone

import ai_engine
from database import DB_PATH

log = logging.getLogger(__name__)


async def generate_and_queue(account_id: int, topic: str, count: int = 5,
                              niche: str = "", language: str = "ru",
                              spread_hours: int = 24):
    """Generate `count` posts and schedule them spread over `spread_hours`."""
    posts = await ai_engine.generate_post_batch(topic, count, niche, language)
    if not posts:
        return {"success": False, "error": "AI returned no posts. Check API key."}

    now = datetime.now(timezone.utc)
    step = max(1, spread_hours * 60 // max(1, count))  # minutes between posts
    queued = 0

    async with aiosqlite.connect(DB_PATH) as db:
        # Ensure scheduled_posts has a created_at default; we just insert.
        for i, text in enumerate(posts):
            scheduled_at = (now + timedelta(minutes=step * (i + 1))
                            + timedelta(minutes=random.randint(-5, 5))).isoformat()
            try:
                await db.execute(
                    "INSERT INTO scheduled_posts (account_id, text, scheduled_at, status) VALUES (?,?,?, 'pending')",
                    (account_id, text, scheduled_at),
                )
                queued += 1
            except Exception as e:
                log.warning("queue insert failed: %s", e)
        await db.commit()

    return {"success": True, "queued": queued, "posts": posts}


async def generate_for_all_accounts(topic: str, count_per_account: int = 3,
                                    niche: str = "", language: str = "ru"):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM accounts WHERE status = 'active'")
        rows = await cur.fetchall()
    total = 0
    for (acc_id,) in rows:
        r = await generate_and_queue(acc_id, topic, count_per_account, niche, language)
        if r.get("success"):
            total += r["queued"]
        await asyncio.sleep(random.uniform(2, 4))
    return {"success": True, "total_queued": total, "accounts": len(rows)}
