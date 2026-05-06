"""
Threads Bot Factory — Database Module (v2 — Multi-User SaaS)
SQLite database for storing users, accounts, proxies, templates, scheduled posts.

DB path priority:
  1. $DB_PATH env var  (set in Koyeb to /app/data/bot_factory.db)
  2. ./bot_factory.db  (local fallback)
"""

import aiosqlite
import json
import os
import shutil
from datetime import datetime

_DEFAULT_LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_factory.db")
DB_PATH = os.environ.get("DB_PATH") or _DEFAULT_LOCAL

os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)) or ".", exist_ok=True)

# Auto-migrate legacy DB
if (
    DB_PATH != _DEFAULT_LOCAL
    and os.path.exists(_DEFAULT_LOCAL)
    and not os.path.exists(DB_PATH)
):
    try:
        shutil.copy2(_DEFAULT_LOCAL, DB_PATH)
        print(f"[db] migrated legacy DB → {DB_PATH}")
    except Exception as e:
        print(f"[db] legacy migration failed: {e}")

print(f"[db] using {DB_PATH}")


async def init_db():
    """Initialize database tables (v2 multi-user)"""
    async with aiosqlite.connect(DB_PATH) as db:

        # ── Users (Telegram login) ─────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id     INTEGER UNIQUE NOT NULL,
                username        TEXT DEFAULT '',
                first_name      TEXT DEFAULT '',
                plan            TEXT DEFAULT 'free',
                is_admin        INTEGER DEFAULT 0,
                accounts_limit  INTEGER DEFAULT 3,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen       TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── Accounts (Threads) ─────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
                username        TEXT NOT NULL,
                threads_user_id TEXT,
                access_token    TEXT NOT NULL,
                token_expires_at TEXT,
                proxy_id        INTEGER,
                status          TEXT DEFAULT 'active',
                followers       INTEGER DEFAULT 0,
                following       INTEGER DEFAULT 0,
                posts_count     INTEGER DEFAULT 0,
                posts_today     INTEGER DEFAULT 0,
                daily_limit     INTEGER DEFAULT 25,
                auto_reply      INTEGER DEFAULT 0,
                auto_post       INTEGER DEFAULT 0,
                reply_style     TEXT DEFAULT 'friendly',
                notes           TEXT DEFAULT '',
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                last_activity   TEXT
            )
        """)

        # ── Proxies ────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS proxies (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER REFERENCES users(id) ON DELETE CASCADE,
                host         TEXT NOT NULL,
                port         INTEGER NOT NULL,
                username     TEXT DEFAULT '',
                password     TEXT DEFAULT '',
                protocol     TEXT DEFAULT 'https',
                status       TEXT DEFAULT 'active',
                country      TEXT DEFAULT '',
                response_time INTEGER DEFAULT 0,
                last_check   TEXT,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── Templates ──────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
                name        TEXT NOT NULL,
                category    TEXT DEFAULT 'general',
                content     TEXT NOT NULL,
                use_spintax INTEGER DEFAULT 1,
                usage_count INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── Scheduled Posts ────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER REFERENCES users(id) ON DELETE CASCADE,
                account_ids  TEXT NOT NULL,
                content      TEXT NOT NULL,
                media_type   TEXT DEFAULT 'text',
                use_spintax  INTEGER DEFAULT 0,
                scheduled_at TEXT NOT NULL,
                status       TEXT DEFAULT 'pending',
                published_at TEXT,
                error        TEXT,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── Post Log ───────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS post_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
                account_id INTEGER,
                thread_id  TEXT,
                content    TEXT,
                status     TEXT,
                error      TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── Auto-Reply Log ─────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_replies (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id   INTEGER,
                comment_id   TEXT UNIQUE,
                post_id      TEXT,
                comment_text TEXT,
                reply_text   TEXT,
                sentiment    TEXT,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── Automation Tasks ───────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS automation_tasks (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id           INTEGER REFERENCES users(id) ON DELETE CASCADE,
                task_type         TEXT NOT NULL,
                account_ids       TEXT NOT NULL,
                config            TEXT NOT NULL,
                status            TEXT DEFAULT 'running',
                progress          INTEGER DEFAULT 0,
                total_actions     INTEGER DEFAULT 0,
                completed_actions INTEGER DEFAULT 0,
                started_at        TEXT DEFAULT CURRENT_TIMESTAMP,
                last_action_at    TEXT
            )
        """)

        # ── Web Sessions ───────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS web_sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL
            )
        """)

        await db.commit()


# ════════════════════════════════════════════════════════════════════════════
# USERS
# ════════════════════════════════════════════════════════════════════════════

async def get_or_create_user(telegram_id: int, username: str = "", first_name: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cur.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET last_seen = ?, username = ?, first_name = ? WHERE telegram_id = ?",
                (datetime.now().isoformat(), username, first_name, telegram_id)
            )
            await db.commit()
            cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = await cur.fetchone()
            return dict(row)
        cursor = await db.execute(
            "INSERT INTO users (telegram_id, username, first_name) VALUES (?, ?, ?)",
            (telegram_id, username, first_name)
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,))
        return dict(await cur.fetchone())


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_user_by_telegram(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def update_user(user_id: int, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [user_id]
        await db.execute(f"UPDATE users SET {sets} WHERE id = ?", vals)
        await db.commit()


async def get_all_users() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users ORDER BY created_at DESC")
        return [dict(r) for r in await cur.fetchall()]


# ════════════════════════════════════════════════════════════════════════════
# WEB SESSIONS
# ════════════════════════════════════════════════════════════════════════════

async def create_session(token: str, user_id: int, expires_at: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO web_sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at)
        )
        await db.commit()


async def get_session(token: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM web_sessions WHERE token = ? AND expires_at > ?",
            (token, datetime.now().isoformat())
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def delete_session(token: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM web_sessions WHERE token = ?", (token,))
        await db.commit()


# ════════════════════════════════════════════════════════════════════════════
# ACCOUNTS
# ════════════════════════════════════════════════════════════════════════════

async def add_account(username: str, access_token: str, threads_user_id: str = "",
                      notes: str = "", user_id: int = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO accounts (username, access_token, threads_user_id, notes, user_id) VALUES (?, ?, ?, ?, ?)",
            (username, access_token, threads_user_id, notes, user_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_accounts(status: str = None, user_id: int = None) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        conditions = []
        params = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if user_id is not None:
            conditions.append("user_id = ?")
            params.append(user_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        cur = await db.execute(f"SELECT * FROM accounts {where} ORDER BY id", params)
        return [dict(r) for r in await cur.fetchall()]


async def get_account(account_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
        row = await cur.fetchone()
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


# ════════════════════════════════════════════════════════════════════════════
# PROXIES
# ════════════════════════════════════════════════════════════════════════════

async def add_proxy(host: str, port: int, username: str = "", password: str = "",
                    protocol: str = "https", country: str = "", user_id: int = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO proxies (host, port, username, password, protocol, country, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (host, port, username, password, protocol, country, user_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_proxies(status: str = None, user_id: int = None) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        conditions = []
        params = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if user_id is not None:
            conditions.append("user_id = ?")
            params.append(user_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        cur = await db.execute(f"SELECT * FROM proxies {where} ORDER BY id", params)
        return [dict(r) for r in await cur.fetchall()]


async def delete_proxy(proxy_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM proxies WHERE id = ?", (proxy_id,))
        await db.commit()


# ════════════════════════════════════════════════════════════════════════════
# TEMPLATES
# ════════════════════════════════════════════════════════════════════════════

async def add_template(name: str, content: str, category: str = "general",
                       use_spintax: int = 1, user_id: int = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO templates (name, content, category, use_spintax, user_id) VALUES (?, ?, ?, ?, ?)",
            (name, content, category, use_spintax, user_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_templates(user_id: int = None) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if user_id is not None:
            cur = await db.execute("SELECT * FROM templates WHERE user_id = ? ORDER BY id", (user_id,))
        else:
            cur = await db.execute("SELECT * FROM templates ORDER BY id")
        return [dict(r) for r in await cur.fetchall()]


async def get_template(template_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def delete_template(template_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        await db.commit()


async def increment_template_usage(template_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE templates SET usage_count = usage_count + 1 WHERE id = ?", (template_id,))
        await db.commit()


# ════════════════════════════════════════════════════════════════════════════
# SCHEDULED POSTS
# ════════════════════════════════════════════════════════════════════════════

async def add_scheduled_post(account_ids: list, content: str, scheduled_at: str,
                              media_type: str = "text", use_spintax: int = 0,
                              user_id: int = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO scheduled_posts (account_ids, content, scheduled_at, media_type, use_spintax, user_id) VALUES (?, ?, ?, ?, ?, ?)",
            (json.dumps(account_ids), content, scheduled_at, media_type, use_spintax, user_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_posts() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM scheduled_posts WHERE status = 'pending' AND scheduled_at <= ? ORDER BY scheduled_at",
            (datetime.now().isoformat(),)
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_scheduled_posts(user_id: int = None) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if user_id is not None:
            cur = await db.execute(
                "SELECT * FROM scheduled_posts WHERE user_id = ? ORDER BY scheduled_at DESC LIMIT 50",
                (user_id,)
            )
        else:
            cur = await db.execute("SELECT * FROM scheduled_posts ORDER BY scheduled_at DESC LIMIT 50")
        return [dict(r) for r in await cur.fetchall()]


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


# ════════════════════════════════════════════════════════════════════════════
# POST LOG & STATS
# ════════════════════════════════════════════════════════════════════════════

async def log_post(account_id: int, content: str, status: str,
                   thread_id: str = None, error: str = None, user_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO post_log (account_id, thread_id, content, status, error, user_id) VALUES (?, ?, ?, ?, ?, ?)",
            (account_id, thread_id, content, status, error, user_id)
        )
        await db.commit()


async def get_post_stats(user_id: int = None) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        uid_filter = "AND user_id = ?" if user_id else ""
        uid_params = (user_id,) if user_id else ()

        cur = await db.execute(f"SELECT COUNT(*) FROM post_log WHERE 1=1 {uid_filter}", uid_params)
        total = (await cur.fetchone())[0]

        cur = await db.execute(f"SELECT COUNT(*) FROM post_log WHERE status = 'success' {uid_filter}", uid_params)
        success = (await cur.fetchone())[0]

        today = datetime.now().strftime("%Y-%m-%d")
        cur = await db.execute(
            f"SELECT COUNT(*) FROM post_log WHERE created_at LIKE ? {uid_filter}",
            (f"{today}%",) + uid_params
        )
        today_count = (await cur.fetchone())[0]

        acc_filter = "WHERE user_id = ?" if user_id else ""
        cur = await db.execute(f"SELECT COUNT(*) FROM accounts {acc_filter}", uid_params)
        accounts = (await cur.fetchone())[0]

        cur = await db.execute(
            f"SELECT COUNT(*) FROM accounts WHERE status = 'active' {'AND user_id = ?' if user_id else ''}",
            uid_params
        )
        active = (await cur.fetchone())[0]

        return {
            "total_posts": total,
            "success_posts": success,
            "today_posts": today_count,
            "total_accounts": accounts,
            "active_accounts": active,
            "success_rate": round(success / total * 100, 1) if total > 0 else 100,
        }
