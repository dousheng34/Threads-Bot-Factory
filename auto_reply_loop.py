"""
Auto-Reply Loop.
Polls each account's recent posts and mentions, generates AI replies
to fresh comments, and posts them back. Built-in rate limiting and dedup.

Integrate with apscheduler in bot.py:

    from auto_reply_loop import run_auto_reply_cycle
    scheduler.add_job(run_auto_reply_cycle, 'interval', minutes=10)
"""
import os, asyncio, random, logging, json
import aiosqlite
from datetime import datetime, timezone

import ai_engine
import threads_engagement as tg
from database import DB_PATH

log = logging.getLogger(__name__)

MIN_DELAY = int(os.getenv("AI_REPLY_DELAY_MIN", "60"))
MAX_DELAY = int(os.getenv("AI_REPLY_DELAY_MAX", "300"))
DAILY_REPLY_LIMIT = int(os.getenv("AI_REPLY_DAILY_LIMIT", "40"))
SKIP_TOXIC = os.getenv("AI_SKIP_TOXIC", "true").lower() == "true"
REPLY_STYLE = os.getenv("AI_REPLY_STYLE", "friendly")
ENABLED = os.getenv("AI_REPLY_ENABLED", "false").lower() == "true"


async def _ensure_table():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                comment_id TEXT UNIQUE,
                post_id TEXT,
                comment_text TEXT,
                reply_text TEXT,
                sentiment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def _seen(comment_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM ai_replies WHERE comment_id = ?", (comment_id,))
        return await cur.fetchone() is not None


async def _record(account_id, comment_id, post_id, comment_text, reply_text, sentiment):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO ai_replies (account_id, comment_id, post_id, comment_text, reply_text, sentiment) VALUES (?,?,?,?,?,?)",
            (account_id, comment_id, post_id, comment_text, reply_text, sentiment),
        )
        await db.commit()


async def _today_count(account_id) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM ai_replies WHERE account_id = ? AND DATE(created_at) = DATE('now')",
            (account_id,),
        )
        return (await cur.fetchone())[0]


async def _all_active_accounts():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, threads_user_id, access_token, username FROM accounts WHERE status = 'active'"
        )
        rows = await cur.fetchall()
    return rows


async def _process_account(account_id, threads_user_id, token, username):
    used = await _today_count(account_id)
    if used >= DAILY_REPLY_LIMIT:
        return

    # Recent own posts
    posts = await tg.list_user_threads(threads_user_id, token, limit=10)
    for p in posts:
        replies = await tg.list_replies(p["id"], token)
        for c in replies:
            cid = c.get("id")
            if not cid:
                continue
            # Skip our own comments
            frm = (c.get("from") or {}).get("id")
            if frm == threads_user_id:
                continue
            if await _seen(cid):
                continue
            text = (c.get("text") or "").strip()
            if not text:
                continue

            sentiment = await ai_engine.analyze_sentiment(text)
            if SKIP_TOXIC and sentiment == "toxic":
                # Optionally hide toxic
                try:
                    await tg.hide_reply(cid, token, hide=True)
                except Exception:
                    pass
                await _record(account_id, cid, p["id"], text, "", sentiment)
                continue

            reply = await ai_engine.generate_reply(text, p.get("text", ""), style=REPLY_STYLE)
            if not reply:
                continue

            # Human-like delay
            await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            res = await tg.reply_to(threads_user_id, token, reply, cid)
            if res.get("success"):
                await _record(account_id, cid, p["id"], text, reply, sentiment)
                log.info("[%s] replied to %s", username, cid)
                used += 1
                if used >= DAILY_REPLY_LIMIT:
                    return
            else:
                log.warning("[%s] reply failed: %s", username, res.get("error"))


async def run_auto_reply_cycle():
    if not ENABLED:
        return
    await _ensure_table()
    accounts = await _all_active_accounts()
    log.info("AI auto-reply cycle: %d accounts", len(accounts))
    for acc in accounts:
        try:
            await _process_account(*acc)
        except Exception as e:
            log.exception("auto-reply failed for %s: %s", acc[3], e)
        await asyncio.sleep(random.uniform(5, 15))
