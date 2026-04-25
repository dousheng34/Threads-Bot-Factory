"""
Threads Bot Factory — Database Module
SQLite database for storing accounts, proxies, templates, scheduled posts
"""

import aiosqlite
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_factory.db")


async def init_db():
    """Initialize database tables"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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

        await db.commit()


# ---- Accounts ----

async def add_account(username: str, access_token: str, threads_user_id: str = "", notes: str = "") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO accounts (username, access_token, threads_user_id, notes) VALUES (?, ?, ?, ?)",
            (username, access_token, threads_user_id, notes)
        )
        await db.commit()
        return cursor.lastrowid


async def get_accounts(status: str = None) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute("SELECT * FROM accounts WHERE status = ?", (status,))
        else:
            cursor = await db.execute("SELECT * FROM accounts ORDER BY id")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_account(account_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_account(account_id: int, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [account_id]
        await db.execute(f"UPDATE accounts SET {sets} WHERE id = ?", vals)
        await db.commit()


async def delete_account(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
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
        await db.commit()


# ---- Proxies ----

async def add_proxy(host: str, port: int, username: str = "", password: str = "",
                    protocol: str = "https", country: str = "") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO proxies (host, port, username, password, protocol, country) VALUES (?, ?, ?, ?, ?, ?)",
            (host, port, username, password, protocol, country)
        )
        await db.commit()
        return cursor.lastrowid


async def get_proxies(status: str = None) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute("SELECT * FROM proxies WHERE status = ?", (status,))
        else:
            cursor = await db.execute("SELECT * FROM proxies ORDER BY id")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_proxy(proxy_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM proxies WHERE id = ?", (proxy_id,))
        await db.commit()


# ---- Templates ----

async def add_template(name: str, content: str, category: str = "general", use_spintax: int = 1) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO templates (name, content, category, use_spintax) VALUES (?, ?, ?, ?)",
            (name, content, category, use_spintax)
        )
        await db.commit()
        return cursor.lastrowid


async def get_templates() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM templates ORDER BY id")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_template(template_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_template(template_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        await db.commit()


async def increment_template_usage(template_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE templates SET usage_count = usage_count + 1 WHERE id = ?", (template_id,))
        await db.commit()


# ---- Scheduled Posts ----

async def add_scheduled_post(account_ids: list, content: str, scheduled_at: str,
                              media_type: str = "text", use_spintax: int = 0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO scheduled_posts (account_ids, content, scheduled_at, media_type, use_spintax) VALUES (?, ?, ?, ?, ?)",
            (json.dumps(account_ids), content, scheduled_at, media_type, use_spintax)
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


async def get_scheduled_posts() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM scheduled_posts ORDER BY scheduled_at DESC LIMIT 20")
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


async def delete_scheduled_post(post_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM scheduled_posts WHERE id = ?", (post_id,))
        await db.commit()


# ---- Post Log ----

async def log_post(account_id: int, content: str, status: str, thread_id: str = None, error: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO post_log (account_id, thread_id, content, status, error) VALUES (?, ?, ?, ?, ?)",
            (account_id, thread_id, content, status, error)
        )
        await db.commit()


async def get_post_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        # Total posts
        cursor = await db.execute("SELECT COUNT(*) FROM post_log")
        total = (await cursor.fetchone())[0]

        # Success
        cursor = await db.execute("SELECT COUNT(*) FROM post_log WHERE status = 'success'")
        success = (await cursor.fetchone())[0]

        # Today
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = await db.execute("SELECT COUNT(*) FROM post_log WHERE created_at LIKE ?", (f"{today}%",))
        today_count = (await cursor.fetchone())[0]

        # Accounts
        cursor = await db.execute("SELECT COUNT(*) FROM accounts")
        accounts = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM accounts WHERE status = 'active'")
        active = (await cursor.fetchone())[0]

        # Proxies
        cursor = await db.execute("SELECT COUNT(*) FROM proxies WHERE status = 'active'")
        active_proxies = (await cursor.fetchone())[0]

        return {
            "total_posts": total,
            "success_posts": success,
            "today_posts": today_count,
            "total_accounts": accounts,
            "active_accounts": active,
            "active_proxies": active_proxies,
            "success_rate": round(success / total * 100, 1) if total > 0 else 100,
        }
