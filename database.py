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
              async with aiosqlite.
