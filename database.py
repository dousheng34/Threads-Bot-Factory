"""
Threads Bot Factory - Database Module
"""

import aiosqlite
import json
import os
import uuid
from datetime import datetime, timedelta

DB_PATH = "bot_factory.db"

PLANS = {
    "free":     {"name": "Free",     "accounts": 1,   "daily_posts": 10,  "ai_requests": 0,   "price": 0,    "days": 0},
    "pro":      {"name": "Pro",      "accounts": 10,  "daily_posts": 999, "ai_requests": 50,  "price": 990,  "days": 30},
    "business": {"name": "Business", "accounts": 999, "daily_posts": 999, "ai_requests": 999, "price": 4990, "days": 30},
}


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                plan TEXT DEFAULT 'free',
                plan_expires_at TEXT,
                ai_requests_today INTEGER DEFAULT 0,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                is_owner INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                username TEXT NOT NULL,
                threads_user_id TEXT,
                access_token TEXT NOT NULL,
                token_expires_at TEXT,
                proxy_id INTEGER,
                status TEXT DEFAULT 'active',
                followers INTEGER DEFAULT 0,
                following INTEGER DEFAULT 0,
                posts_count INTEGER DEFAULT 0,
                posts_today INTEGER DEFAULT 0,
                daily_limit INTEGER DEFAULT 25,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_activity TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                username TEXT DEFAULT '',
                password TEXT DEFAULT '',
                protocol TEXT DEFAULT 'https',
                status TEXT DEFAULT 'active',
                country TEXT DEFAULT '',
                response_time INTEGER DEFAULT 0,
                last_check TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                use_spintax INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                account_ids TEXT NOT NULL,
                content TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                error TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS post_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                account_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL,
                thread_id TEXT,
                error TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan TEXT NOT NULL,
                amount INTEGER NOT NULL,
                method TEXT DEFAULT 'manual',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TEXT
            )
        """)
        await db.commit()


async def get_or_create_user(telegram_id: int, username: str = "", full_name: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET last_active = ?, username = ?, full_name = ? WHERE telegram_id = ?",
                (datetime.now().isoformat(), username or "", full_name or "", telegram_id)
            )
            await db.commit()
            return dict(row)
        ref_code = str(uuid.uuid4())[:8].upper()
        cursor = await db.execute(
            "INSERT INTO users (telegram_id, username, full_name, plan, referral_code, last_active) VALUES (?,?,?,?,?,?)",
            (telegram_id, username or "", full_name or "", "free", ref_code, datetime.now().isoformat())
        )
        await db.commit()
        cursor2 = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row2 = await cursor2.fetchone()
        return dict(row2)


async def get_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_plan(telegram_id: int) -> dict:
    user = await get_user(telegram_id)
    if not user:
        return PLANS["free"]
    plan = user.get("plan", "free")
    expires = user.get("plan_expires_at")
    if plan != "free" and expires:
        if datetime.fromisoformat(expires) < datetime.now():
            await downgrade_to_free(telegram_id)
            return PLANS["free"]
    return PLANS.get(plan, PLANS["free"])


async def upgrade_user_plan(telegram_id: int, plan: str, days: int = 30):
    expires = (datetime.now() + timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET plan = ?, plan_expires_at = ? WHERE telegram_id = ?",
            (plan, expires, telegram_id)
        )
        await db.commit()


async def downgrade_to_free(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET plan = 'free', plan_expires_at = NULL WHERE telegram_id = ?",
            (telegram_id,)
        )
        await db.commit()


async def get_user_stats_count() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) as total FROM users")
        row = await cursor.fetchone()
        total = row[0] if row else 0
        cursor2 = await db.execute("SELECT COUNT(*) as paid FROM users WHERE plan != 'free'")
        row2 = await cursor2.fetchone()
        paid = row2[0] if row2 else 0
        return {"total": total, "paid": paid, "free": total - paid}


async def apply_referral(new_user_id: int, ref_code: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT telegram_id FROM users WHERE referral_code = ?", (ref_code,))
        referrer = await cursor.fetchone()
        if not referrer:
            return False
        referrer_id = referrer["telegram_id"]
        if referrer_id == new_user_id:
            return False
        await db.execute(
            "UPDATE users SET referred_by = ? WHERE telegram_id = ?",
            (referrer_id, new_user_id)
        )
        await db.commit()
        return True


async def get_referral_count(telegram_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (telegram_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def add_account(username: str, access_token: str, threads_user_id: str = "", user_id: int = 0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO accounts (username, access_token, threads_user_id, user_id, created_at) VALUES (?,?,?,?,?)",
            (username, access_token, threads_user_id, user_id, datetime.now().isoformat())
        )
        await db.commit()
        return cursor.lastrowid


async def get_accounts(status: str = None, user_id: int = 0) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if user_id:
            if status:
                cursor = await db.execute("SELECT * FROM accounts WHERE user_id = ? AND status = ?", (user_id, status))
            else:
                cursor = await db.execute("SELECT * FROM accounts WHERE user_id = ?", (user_id,))
        else:
            if status:
                cursor = await db.execute("SELECT * FROM accounts WHERE status = ?", (status,))
            else:
                cursor = await db.execute("SELECT * FROM accounts")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_account(account_id: int, user_id: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if user_id:
            cursor = await db.execute("SELECT * FROM accounts WHERE id = ? AND user_id = ?", (account_id, user_id))
        else:
            cursor = await db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_account(account_id: int, user_id: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id:
            await db.execute("DELETE FROM accounts WHERE id = ? AND user_id = ?", (account_id, user_id))
        else:
            await db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        await db.commit()


async def increment_posts_today(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE accounts SET posts_today = posts_today + 1, posts_count = posts_count + 1, last_activity = ? WHERE id = ?",
            (datetime.now().isoformat(), account_id)
        )
        await db.commit()


async def reset_daily_posts():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE accounts SET posts_today = 0")
        await db.execute("UPDATE users SET ai_requests_today = 0")
        await db.commit()


async def add_proxy(host: str, port: int, username: str = "", password: str = "", protocol: str = "https", user_id: int = 0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO proxies (host, port, username, password, protocol, user_id, created_at) VALUES (?,?,?,?,?,?,?)",
            (host, port, username, password, protocol, user_id, datetime.now().isoformat())
        )
        await db.commit()
        return cursor.lastrowid


async def get_proxies(status: str = None, user_id: int = 0) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if user_id:
            if status:
                cursor = await db.execute("SELECT * FROM proxies WHERE user_id = ? AND status = ?", (user_id, status))
            else:
                cursor = await db.execute("SELECT * FROM proxies WHERE user_id = ?", (user_id,))
        else:
            if status:
                cursor = await db.execute("SELECT * FROM proxies WHERE status = ?", (status,))
            else:
                cursor = await db.execute("SELECT * FROM proxies")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def delete_proxy(proxy_id: int, user_id: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id:
            await db.execute("DELETE FROM proxies WHERE id = ? AND user_id = ?", (proxy_id, user_id))
        else:
            await db.execute("DELETE FROM proxies WHERE id = ?", (proxy_id,))
        await db.commit()


async def add_template(name: str, content: str, category: str = "general", use_spintax: bool = False, user_id: int = 0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO templates (name, content, category, use_spintax, user_id, created_at) VALUES (?,?,?,?,?,?)",
            (name, content, category, int(use_spintax), user_id, datetime.now().isoformat())
        )
        await db.commit()
        return cursor.lastrowid


async def get_templates(user_id: int = 0) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if user_id:
            cursor = await db.execute("SELECT * FROM templates WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        else:
            cursor = await db.execute("SELECT * FROM templates ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def delete_template(template_id: int, user_id: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id:
            await db.execute("DELETE FROM templates WHERE id = ? AND user_id = ?", (template_id, user_id))
        else:
            await db.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        await db.commit()


async def add_scheduled_post(account_ids: list, content: str, scheduled_at: str, user_id: int = 0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO scheduled_posts (account_ids, content, scheduled_at, user_id, created_at) VALUES (?,?,?,?,?)",
            (json.dumps(account_ids), content, scheduled_at, user_id, datetime.now().isoformat())
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_posts() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        now = datetime.now().isoformat()
        cursor = await db.execute(
            "SELECT * FROM scheduled_posts WHERE status = 'pending' AND scheduled_at <= ? ORDER BY scheduled_at",
            (now,)
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["account_ids"] = json.loads(d["account_ids"])
            result.append(d)
        return result


async def get_scheduled_posts(user_id: int = 0) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if user_id:
            cursor = await db.execute(
                "SELECT * FROM scheduled_posts WHERE user_id = ? ORDER BY scheduled_at DESC",
                (user_id,)
            )
        else:
            cursor = await db.execute("SELECT * FROM scheduled_posts ORDER BY scheduled_at DESC")
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["account_ids"] = json.loads(d["account_ids"])
            result.append(d)
        return result


async def update_post_status(post_id: int, status: str, error: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE scheduled_posts SET status = ?, error = ? WHERE id = ?",
            (status, error, post_id)
        )
        await db.commit()


async def delete_scheduled_post(post_id: int, user_id: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id:
            await db.execute("DELETE FROM scheduled_posts WHERE id = ? AND user_id = ?", (post_id, user_id))
        else:
            await db.execute("DELETE FROM scheduled_posts WHERE id = ?", (post_id,))
        await db.commit()


async def log_post(account_id: int, content: str, status: str, thread_id: str = "", error: str = "", user_id: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO post_logs (account_id, content, status, thread_id, error, user_id, created_at) VALUES (?,?,?,?,?,?,?)",
            (account_id, content, status, thread_id, error, user_id, datetime.now().isoformat())
        )
        await db.commit()


async def get_post_stats(user_id: int = 0) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id:
            cursor = await db.execute("SELECT COUNT(*) FROM post_logs WHERE user_id = ?", (user_id,))
        else:
            cursor = await db.execute("SELECT COUNT(*) FROM post_logs")
        total = (await cursor.fetchone())[0]

        if user_id:
            cursor = await db.execute("SELECT COUNT(*) FROM post_logs WHERE status = 'success' AND user_id = ?", (user_id,))
        else:
            cursor = await db.execute("SELECT COUNT(*) FROM post_logs WHERE status = 'success'")
        success = (await cursor.fetchone())[0]

        if user_id:
            cursor = await db.execute("SELECT COUNT(*) FROM post_logs WHERE status = 'error' AND user_id = ?", (user_id,))
        else:
            cursor = await db.execute("SELECT COUNT(*) FROM post_logs WHERE status = 'error'")
        errors = (await cursor.fetchone())[0]

        today = datetime.now().date().isoformat()
        if user_id:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM post_logs WHERE date(created_at) = ? AND user_id = ?", (today, user_id)
            )
        else:
            cursor = await db.execute("SELECT COUNT(*) FROM post_logs WHERE date(created_at) = ?", (today,))
        today_count = (await cursor.fetchone())[0]

        return {"total": total, "success": success, "errors": errors, "today": today_count}


async def create_payment(user_id: int, plan: str, amount: int, method: str = "manual") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO payments (user_id, plan, amount, method, created_at) VALUES (?,?,?,?,?)",
            (user_id, plan, amount, method, datetime.now().isoformat())
        )
        await db.commit()
        return cursor.lastrowid


async def confirm_payment(payment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        payment = await cursor.fetchone()
        if not payment:
            return False
        payment = dict(payment)
        plan_info = PLANS.get(payment["plan"], PLANS["free"])
        await upgrade_user_plan(payment["user_id"], payment["plan"], plan_info["days"])
        await db.execute(
            "UPDATE payments SET status = 'confirmed', confirmed_at = ? WHERE id = ?",
            (datetime.now().isoformat(), payment_id)
        )
        await db.commit()
        return True


async def get_pending_payments() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT p.*, u.username, u.telegram_id FROM payments p LEFT JOIN users u ON p.user_id = u.telegram_id WHERE p.status = 'pending' ORDER BY p.created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_all_users() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def set_owner(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_owner = 1 WHERE telegram_id = ?", (telegram_id,))
        await db.commit()
