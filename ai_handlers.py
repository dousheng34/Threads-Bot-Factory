"""
Telegram aiogram handlers for the AI suite.
Register in bot.py:

    from ai_handlers import register_ai_handlers
    register_ai_handlers(dp)

Adds commands:
    /ai_reply_on    — turn auto-reply on (this process)
    /ai_reply_off   — turn it off
    /ai_reply_now   — run one cycle immediately
    /ai_post <topic> | <count> | <niche> — generate posts for active accounts
    /ai_stats       — AI activity stats
    /ai_test <text> — quick AI ping
    /backup         — download the SQLite DB file via Telegram
    /restore        — reply to a .db file with this command to overwrite the DB
"""
import os, asyncio, logging, shutil, tempfile, time
import aiosqlite
from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile

import ai_engine
import auto_reply_loop
import ai_post_generator
from database import DB_PATH

log = logging.getLogger(__name__)

ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(";", ",").split(",") if x.strip().isdigit()}


def _is_admin(uid: int) -> bool:
    return not ADMIN_IDS or uid in ADMIN_IDS


async def cmd_ai_reply_on(msg: types.Message):
    if not _is_admin(msg.from_user.id): return
    auto_reply_loop.ENABLED = True
    os.environ["AI_REPLY_ENABLED"] = "true"
    await msg.answer("\u2705 AI auto-reply: ON")


async def cmd_ai_reply_off(msg: types.Message):
    if not _is_admin(msg.from_user.id): return
    auto_reply_loop.ENABLED = False
    os.environ["AI_REPLY_ENABLED"] = "false"
    await msg.answer("\u23f8 AI auto-reply: OFF")


async def cmd_ai_reply_now(msg: types.Message):
    if not _is_admin(msg.from_user.id): return
    await msg.answer("\U0001f504 Running auto-reply cycle...")
    prev = auto_reply_loop.ENABLED
    auto_reply_loop.ENABLED = True
    try:
        await auto_reply_loop.run_auto_reply_cycle()
        await msg.answer("\u2705 Cycle done")
    except Exception as e:
        await msg.answer(f"\u274c Error: {e}")
    finally:
        auto_reply_loop.ENABLED = prev


async def cmd_ai_post(msg: types.Message):
    if not _is_admin(msg.from_user.id): return
    raw = msg.text.split(maxsplit=1)
    if len(raw) < 2:
        await msg.answer("Usage: /ai_post topic | count | niche\nExample: /ai_post AI startups | 5 | tech")
        return
    parts = [p.strip() for p in raw[1].split("|")]
    topic = parts[0]
    count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 3
    niche = parts[2] if len(parts) > 2 else ""
    await msg.answer(f"\U0001f9e0 Generating {count} posts per active account...")
    r = await ai_post_generator.generate_for_all_accounts(topic, count, niche)
    await msg.answer(f"\u2705 Queued {r['total_queued']} posts across {r['accounts']} accounts")


async def cmd_ai_stats(msg: types.Message):
    if not _is_admin(msg.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            cur = await db.execute("SELECT COUNT(*), COUNT(DISTINCT account_id) FROM ai_replies")
            total, accs = await cur.fetchone()
            cur = await db.execute("SELECT COUNT(*) FROM ai_replies WHERE DATE(created_at) = DATE('now')")
            today = (await cur.fetchone())[0]
            cur = await db.execute("SELECT sentiment, COUNT(*) FROM ai_replies GROUP BY sentiment")
            sent_rows = await cur.fetchall()
        except Exception:
            await msg.answer("No AI activity yet.")
            return
    sent = ", ".join(f"{s}: {c}" for s, c in sent_rows) or "-"
    await msg.answer(
        f"\U0001f4ca AI Stats\n"
        f"Total replies: {total}\n"
        f"Today: {today}\n"
        f"Accounts engaged: {accs}\n"
        f"Sentiment: {sent}\n"
        f"Provider: {ai_engine.PROVIDER}\n"
        f"DB path: {DB_PATH}"
    )


async def cmd_ai_test(msg: types.Message):
    if not _is_admin(msg.from_user.id): return
    raw = msg.text.split(maxsplit=1)
    prompt = raw[1] if len(raw) > 1 else "Say hi in Russian."
    out = await ai_engine.chat(prompt)
    await msg.answer(out or "\u274c No response — check AI keys in .env")


# ---------- Backup / Restore ----------

async def cmd_backup(msg: types.Message):
    """Send the SQLite DB file to the admin via Telegram."""
    if not _is_admin(msg.from_user.id): return
    if not os.path.exists(DB_PATH):
        await msg.answer(f"\u274c DB file not found: {DB_PATH}")
        return
    # Use VACUUM INTO for a consistent snapshot
    snap = os.path.join(tempfile.gettempdir(), f"backup_{int(time.time())}.db")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(f"VACUUM INTO ?", (snap,))
        size_kb = os.path.getsize(snap) // 1024
        await msg.answer_document(
            FSInputFile(snap, filename=f"bot_factory_backup.db"),
            caption=f"\ud83d\udcbe Backup\nSource: {DB_PATH}\nSize: {size_kb} KB\n\nReply to this file with /restore to roll back.",
        )
    except Exception as e:
        # Fallback: just copy the file
        try:
            shutil.copy2(DB_PATH, snap)
            await msg.answer_document(
                FSInputFile(snap, filename="bot_factory_backup.db"),
                caption=f"\ud83d\udcbe Backup (raw copy)\n{DB_PATH}",
            )
        except Exception as e2:
            await msg.answer(f"\u274c Backup failed: {e2}")
    finally:
        try: os.remove(snap)
        except Exception: pass


async def cmd_restore(msg: types.Message):
    """Reply to a .db file with /restore to overwrite the live DB."""
    if not _is_admin(msg.from_user.id): return
    reply = msg.reply_to_message
    if not reply or not reply.document:
        await msg.answer("\u26a0\ufe0f Reply to a .db file with /restore.")
        return
    doc = reply.document
    if not (doc.file_name or "").endswith(".db"):
        await msg.answer("\u26a0\ufe0f File must be .db")
        return

    # Save current DB as a safety backup first
    safety = DB_PATH + f".before_restore_{int(time.time())}"
    try:
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, safety)
    except Exception as e:
        await msg.answer(f"\u274c Could not create safety backup: {e}")
        return

    try:
        bot = msg.bot
        f = await bot.get_file(doc.file_id)
        await bot.download_file(f.file_path, destination=DB_PATH)
        await msg.answer(
            f"\u2705 Restored DB → {DB_PATH}\n"
            f"Safety backup of previous DB: {safety}\n\n"
            "\u26a0\ufe0f Restart the service so all modules pick up the new DB."
        )
    except Exception as e:
        await msg.answer(f"\u274c Restore failed: {e}\nPrevious DB preserved at {safety}")


def register_ai_handlers(dp: Dispatcher):
    dp.message.register(cmd_ai_reply_on,  Command("ai_reply_on"))
    dp.message.register(cmd_ai_reply_off, Command("ai_reply_off"))
    dp.message.register(cmd_ai_reply_now, Command("ai_reply_now"))
    dp.message.register(cmd_ai_post,      Command("ai_post"))
    dp.message.register(cmd_ai_stats,     Command("ai_stats"))
    dp.message.register(cmd_ai_test,      Command("ai_test"))
    dp.message.register(cmd_backup,       Command("backup"))
    dp.message.register(cmd_restore,      Command("restore"))
