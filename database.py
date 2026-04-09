"""
Threads Bot Factory - Database Module
Multi-user SQLite database with subscription plans
"""

import aiosqlite
import json
import os
import uuid
from datetime import datetime, timedelta

DB_PATH = "bot_factory.db"

PLANS = {
      "free":     {"name": "Free",     "accounts": 1,   "daily_posts": 10,  "ai_requests": 0,   "price": 0,    "days": 0},
      "pro":      {"name": "Pro",       "accounts": 10,  "daily_posts": 999, "ai_requests": 50,  "price": 990,  "days": 30},
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
                        category TEXT DEFAULT 'general',
                        content TEXT NOT NULL,
                        use_spintax INTEGER DEFAULT 1,
                        usage_count INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS scheduled_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL DEFAULT 0,
                        account_ids TEXT NOT NULL,
                        content TEXT NOT NULL,
                        media_type TEXT DEFAULT 'text',
                        use_spintax INTEGER DEFAULT 0,
                        scheduled_at TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        published_at TEXT,
                        error TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS post_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL DEFAULT 0,
                        account_id INTEGER,
                        thread_id TEXT,
                        content TEXT,
                        status TEXT,
                        error TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS automation_tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL DEFAULT 0,
                        task_type TEXT NOT NULL,
                        account_ids TEXT NOT NULL,
                        config TEXT NOT NULL,
                        status TEXT DEFAULT 'running',
                        progress INTEGER DEFAULT 0,
                        total_actions INTEGER DEFAULT 0,
                        completed_actions INTEGER DEFAULT 0,
                        started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        last_action_at TEXT
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
                        comment TEXT DEFAULT '',
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
                      plan_key = user.get("plan", "free")
    expires = user.get("plan_expires_at")
    if plan_key != "free" and expires:
              if datetime.now().isoformat() > expires:
                            await downgrade_to_free(telegram_id)
                            return PLANS["free"]
                    return PLANS.get(plan_key, PLANS["free"])

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
                c = await db.execute("SELECT COUNT(*) FROM users")
        total = (await c.fetchone())[0]
        c = await db.execute("SELECT COUNT(*) FROM users WHERE plan = 'pro'")
        pro = (await c.fetchone())[0]
        c = await db.execute("SELECT COUNT(*) FROM users WHERE plan = 'business'")
        biz = (await c.fetchone())[0]
        return {"total": total, "free": total - pro - biz, "pro": pro, "business": biz}

async def apply_referral(new_user_id: int, ref_code: str) -> bool:
      async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT telegram_id FROM users WHERE referral_code = ?", (ref_code.upper(),))
        referrer = await c.fetchone()
        if not referrer or referrer["telegram_id"] == new_user_id:
                      return False
                  await db.execute(
                                "UPDATE users SET referred_by = ? WHERE telegram_id = ?",
                                (referrer["telegram_id"], new_user_id)
                  )
        await db.commit()
        return True

async def get_referral_count(telegram_id: int) -> int:
      async with aiosqlite.connect(DB_PATH) as db:
                c = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (telegram_id,))
        return (await c.fetchone())[0]
async def add_account(username: str, access_token: str, threads_user_id: str = "", notes: str = "", user_id: int = 0) -> int:
      async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "INSERT INTO accounts (user_id, username, access_token, threads_user_id, notes) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username, access_token, threads_user_id, notes)
      )
        await db.commit()
        return cursor.lastrowid

async def get_accounts(status: str = None, user_id: int = 0) -> list:
      async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
        if status:
                      cursor = await db.execute("SELECT * FROM accounts WHERE user_id = ? AND status = ?", (user_id, status))
else:
            cursor = await db.execute("SELECT * FROM accounts WHERE user_id = ? ORDER BY id", (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_account(account_id: int, user_id: int = 0):
      async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM accounts WHERE id = ? AND user_id = ?", (account_id, user_id))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def delete_account(account_id: int, user_id: int = 0):
      async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("DELETE FROM accounts WHERE id = ? AND user_id = ?", (account_id, user_id))
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
        await db.commit()

async def add_proxy(host: str, port: int, username: str = "", password: str = "",
                                        protocol: str = "https", country: str = "", user_id: int = 0) -> int:
                                              async with aiosqlite.connect(DB_PATH) as db:
                                                        cursor = await db.execute(
                                                                      "INSERT INTO proxies (user_id, host, port, username, password, protocol, country) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                                                      (user_id, host, port, username, password, protocol, country)
                                                        )
                                                        await db.commit()
                                                        return cursor.lastrowid

                                          async def get_proxies(status: str = None, user_id: int = 0) -> list:
                                                async with aiosqlite.connect(DB_PATH) as db:
                                                          db.row_factory = aiosqlite.Row
                                                          if status:
                                                                        cursor = await db.execute("SELECT * FROM proxies WHERE user_id = ? AND status = ?", (user_id, status))
else:
            cursor = await db.execute("SELECT * FROM proxies WHERE user_id = ? ORDER BY id", (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def delete_proxy(proxy_id: int, user_id: int = 0):
      async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("DELETE FROM proxies WHERE id = ? AND user_id = ?", (proxy_id, user_id))
        await db.commit()

async def add_template(name: str, content: str, category: str = "general", use_spintax: int = 1, user_id: int = 0) -> int:
      async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "INSERT INTO templates (user_id, name, content, category, use_spintax) VALUES (?, ?, ?, ?, ?)",
                    (user_id, name, content, category, use_spintax)
      )
        await db.commit()
        return cursor.lastrowid

async def get_templates(user_id: int = 0) -> list:
      async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM templates WHERE user_id = ? ORDER BY id", (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def delete_template(template_id: int, user_id: int = 0):
      async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("DELETE FROM templates WHERE id = ? AND user_id = ?", (template_id, user_id))
        await db.commit()

async def add_scheduled_post(account_ids: list, content: str, scheduled_at: str,
                                                           media_type: str = "text", use_spintax: int = 0, user_id: int = 0) -> int:
                                                                 async with aiosqlite.connect(DB_PATH) as db:
                                                                           cursor = await db.execute(
                                                                                         "INSERT INTO scheduled_posts (user_id, account_ids, content, scheduled_at, media_type, use_spintax) VALUES (?, ?, ?, ?, ?, ?)",
                                                                                         (user_id, json.dumps(account_ids), content, scheduled_at, media_type, use_spintax)
                                                                           )
                                                                           await db.commit()
                                                                           return cursor.lastrowid

                                                             async def get_pending_posts() -> list:
                                                                   async with aiosqlite.connect(DB_PATH) as db:
                                                                             db.row_factory = aiosqlite.Row
                                                                             cursor = await db.execute(
                                                                                 "SELECT * FROM scheduled_posts WHERE status = 'pending' AND scheduled_at <= ? ORDER BY scheduled_at",
                                                                                 (datetime.now().isoformat(),)
                                                                             )
                                                                             rows = await cursor.fetchall()
                                                                             return [dict(row) for row in rows]

                                                               async def get_scheduled_posts(user_id: int = 0) -> list:
                                                                     async with aiosqlite.connect(DB_PATH) as db:
                                                                               db.row_factory = aiosqlite.Row
                                                                               cursor = await db.execute(
                                                                                   "SELECT * FROM scheduled_posts WHERE user_id = ? ORDER BY scheduled_at DESC LIMIT 20",
                                                                                   (user_id,)
                                                                               )
                                                                               rows = await cursor.fetchall()
                                                                               return [dict(row) for row in rows]

                                                                 async def update_post_status(post_id: int, status: str, error: str = None):
                                                                       async with aiosqlite.connect(DB_PATH) as db:
                                                                                 if status == "published":
                                                                                               await db.execute(
                                                                                                                 "UPDATE scheduled_posts SET status = ?, published_at = ? WHERE id = ?",
                                                                                                                 (status, datetime.now().isoformat(), post_id)
                                                                                                 )
else:
            await db.execute(
                              "UPDATE scheduled_posts SET status = ?, error = ? WHERE id = ?",
                              (status, error, post_id)
            )
        await db.commit()

async def delete_scheduled_post(post_id: int, user_id: int = 0):
      async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("DELETE FROM scheduled_posts WHERE id = ? AND user_id = ?", (post_id, user_id))
        await db.commit()

async def log_post(account_id: int, content: str, status: str, thread_id: str = None, error: str = None, user_id: int = 0):
      async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT INTO post_log (user_id, account_id, thread_id, content, status, error) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, account_id, thread_id, content, status, error)
      )
        await db.commit()

async def get_post_stats(user_id: int = 0) -> dict:
      async with aiosqlite.connect(DB_PATH) as db:
                c = await db.execute("SELECT COUNT(*) FROM post_log WHERE user_id = ?", (user_id,))
        total = (await c.fetchone())[0]
        c = await db.execute("SELECT COUNT(*) FROM post_log WHERE user_id = ? AND status = 'success'", (user_id,))
        success = (await c.fetchone())[0]
        today = datetime.now().strftime("%Y-%m-%d")
        c = await db.execute("SELECT COUNT(*) FROM post_log WHERE user_id = ? AND created_at LIKE ?", (user_id, f"{today}%"))
        today_count = (await c.fetchone())[0]
        c = await db.execute("SELECT COUNT(*) FROM accounts WHERE user_id = ?", (user_id,))
        accounts = (await c.fetchone())[0]
        c = await db.execute("SELECT COUNT(*) FROM accounts WHERE user_id = ? AND status = 'active'", (user_id,))
        active = (await c.fetchone())[0]
        c = await db.execute("SELECT COUNT(*) FROM proxies WHERE user_id = ? AND status = 'active'", (user_id,))
        active_proxies = (await c.fetchone())[0]
        return {
                      "total_posts": total,
                      "success_posts": success,
                      "today_posts": today_count,
                      "total_accounts": accounts,
                      "active_accounts": active,
                      "active_proxies": active_proxies,
                      "success_rate": round(success / total * 100, 1) if total > 0 else 100,
        }

async def create_payment(user_id: int, plan: str, amount: int, method: str = "manual", comment: str = "") -> int:
      async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "INSERT INTO payments (user_id, plan, amount, method, status, comment) VALUES (?, ?, ?, ?, 'pending', ?)",
            (user_id, plan, amount, method, comment)
      )
        await db.commit()
        return cursor.lastrowid

async def confirm_payment(payment_id: int):
      async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
        await db.execute(
                      "UPDATE payments SET status = 'confirmed', confirmed_at = ? WHERE id = ?",
                      (datetime.now().isoformat(), payment_id)
        )
        await db.commit()
        c = await db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        return dict(await c.fetchone())

async def get_pending_payments() -> list:
      async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
        c = await db.execute(
                      "SELECT p.*, u.username, u.telegram_id FROM payments p JOIN users u ON p.user_id = u.telegram_id WHERE p.status = 'pending' ORDER BY p.created_at DESC"
        )
        rows = await c.fetchall()
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
