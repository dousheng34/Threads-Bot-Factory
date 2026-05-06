"""
Threads Bot Factory — Web Dashboard (FastAPI)
Запуск: uvicorn webapp:app --host 0.0.0.0 --port 8000
"""

import os
import secrets
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import database as db
from threads_api import process_spintax, publish_thread, get_user_profile
import ai_engine

app = FastAPI(title="Threads Bot Factory", version="2.0")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_TG_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "30"))

templates = Jinja2Templates(directory="templates")

# ── Telegram Login Auth ──────────────────────────────────────────────────────

def verify_telegram_auth(data: dict) -> bool:
    """Verify Telegram Login Widget data"""
    if not BOT_TOKEN:
        return True  # dev mode
    check_hash = data.pop("hash", "")
    sorted_data = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hashlib.sha256(BOT_TOKEN.encode()).digest()
    expected = hmac.new(secret, sorted_data.encode(), hashlib.sha256).hexdigest()
    # Verify not older than 1 day
    auth_date = int(data.get("auth_date", 0))
    if datetime.now().timestamp() - auth_date > 86400:
        return False
    return hmac.compare_digest(check_hash, expected)


async def get_current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("session_token")
    if not token:
        return None
    session = await db.get_session(token)
    if not session:
        return None
    user = await db.get_user(session["user_id"])
    return user


async def require_user(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ── Auth Routes ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/auth/telegram")
async def auth_telegram(request: Request):
    """Handle Telegram Login Widget callback"""
    params = dict(request.query_params)
    tg_id = int(params.get("id", 0))
    if not tg_id:
        return RedirectResponse("/?error=1")

    # In production, verify hash
    # verify_telegram_auth(params)  # uncomment for production

    user = await db.get_or_create_user(
        telegram_id=tg_id,
        username=params.get("username", ""),
        first_name=params.get("first_name", "")
    )

    # Check if first user → make admin
    all_users = await db.get_all_users()
    if len(all_users) == 1 or tg_id == ADMIN_TG_ID:
        await db.update_user(user["id"], is_admin=1, plan="admin", accounts_limit=999)
        user = await db.get_user(user["id"])

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(days=SESSION_DAYS)).isoformat()
    await db.create_session(token, user["id"], expires_at)

    response = RedirectResponse("/dashboard")
    response.set_cookie("session_token", token, max_age=SESSION_DAYS * 86400, httponly=True)
    return response


@app.post("/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token")
    if token:
        await db.delete_session(token)
    response = RedirectResponse("/")
    response.delete_cookie("session_token")
    return response


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: dict = Depends(require_user)):
    accounts = await db.get_accounts(user_id=user["id"])
    stats = await db.get_post_stats(user_id=user["id"])
    scheduled = await db.get_scheduled_posts(user_id=user["id"])
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "accounts": accounts,
        "stats": stats,
        "scheduled": scheduled,
    })


# ── API: Accounts ─────────────────────────────────────────────────────────────

@app.get("/api/accounts")
async def api_accounts(user: dict = Depends(require_user)):
    accounts = await db.get_accounts(user_id=user["id"])
    return {"accounts": accounts}


@app.post("/api/accounts/add")
async def api_add_account(
    request: Request,
    user: dict = Depends(require_user)
):
    data = await request.json()
    username = data.get("username", "").strip()
    token = data.get("access_token", "").strip()
    user_id_threads = data.get("threads_user_id", "").strip()

    if not username or not token:
        raise HTTPException(400, "username and access_token required")

    # Check plan limits
    existing = await db.get_accounts(user_id=user["id"])
    if len(existing) >= user["accounts_limit"]:
        raise HTTPException(403, f"Лимит аккаунтов: {user['accounts_limit']}. Нужен PRO тариф.")

    acc_id = await db.add_account(username, token, user_id_threads, user_id=user["id"])
    return {"ok": True, "account_id": acc_id}


@app.delete("/api/accounts/{account_id}")
async def api_delete_account(account_id: int, user: dict = Depends(require_user)):
    acc = await db.get_account(account_id)
    if not acc or acc.get("user_id") != user["id"]:
        raise HTTPException(404, "Account not found")
    await db.delete_account(account_id)
    return {"ok": True}


@app.patch("/api/accounts/{account_id}")
async def api_update_account(account_id: int, request: Request, user: dict = Depends(require_user)):
    acc = await db.get_account(account_id)
    if not acc or acc.get("user_id") != user["id"]:
        raise HTTPException(404, "Account not found")
    data = await request.json()
    allowed = {"auto_reply", "auto_post", "reply_style", "daily_limit", "status", "notes"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if updates:
        await db.update_account(account_id, **updates)
    return {"ok": True}


# ── API: Post ─────────────────────────────────────────────────────────────────

@app.post("/api/post/quick")
async def api_quick_post(request: Request, user: dict = Depends(require_user)):
    data = await request.json()
    account_id = data.get("account_id")
    content = data.get("content", "").strip()
    use_spintax = data.get("use_spintax", False)

    if not account_id or not content:
        raise HTTPException(400, "account_id and content required")

    acc = await db.get_account(account_id)
    if not acc or acc.get("user_id") != user["id"]:
        raise HTTPException(404, "Account not found")

    text = process_spintax(content) if use_spintax else content
    result = await publish_thread(acc["threads_user_id"], acc["access_token"], text)

    status = "success" if result.get("success") else "error"
    await db.log_post(account_id, text, status,
                      thread_id=result.get("thread_id"),
                      error=result.get("error"),
                      user_id=user["id"])
    if result.get("success"):
        await db.increment_posts_today(account_id)

    return result


@app.post("/api/post/schedule")
async def api_schedule_post(request: Request, user: dict = Depends(require_user)):
    data = await request.json()
    account_ids = data.get("account_ids", [])
    content = data.get("content", "").strip()
    scheduled_at = data.get("scheduled_at", "")
    use_spintax = data.get("use_spintax", False)

    if not account_ids or not content or not scheduled_at:
        raise HTTPException(400, "account_ids, content, scheduled_at required")

    post_id = await db.add_scheduled_post(
        account_ids=account_ids,
        content=content,
        scheduled_at=scheduled_at,
        use_spintax=1 if use_spintax else 0,
        user_id=user["id"]
    )
    return {"ok": True, "post_id": post_id}


@app.delete("/api/post/schedule/{post_id}")
async def api_delete_scheduled(post_id: int, user: dict = Depends(require_user)):
    posts = await db.get_scheduled_posts(user_id=user["id"])
    if not any(p["id"] == post_id for p in posts):
        raise HTTPException(404, "Post not found")
    await db.delete_scheduled_post(post_id)
    return {"ok": True}


# ── API: AI ───────────────────────────────────────────────────────────────────

@app.post("/api/ai/generate")
async def api_generate_post(request: Request, user: dict = Depends(require_user)):
    data = await request.json()
    topic = data.get("topic", "").strip()
    language = data.get("language", "ru")
    niche = data.get("niche", "")
    count = min(int(data.get("count", 3)), 5)

    if not topic:
        raise HTTPException(400, "topic required")

    posts = await ai_engine.generate_post_batch(topic, count=count, niche=niche, language=language)
    return {"posts": posts}


@app.post("/api/ai/reply-preview")
async def api_reply_preview(request: Request, user: dict = Depends(require_user)):
    data = await request.json()
    comment = data.get("comment", "").strip()
    post_context = data.get("post_context", "")
    style = data.get("style", "friendly")

    if not comment:
        raise HTTPException(400, "comment required")

    reply = await ai_engine.generate_reply(comment, post_context, style=style)
    return {"reply": reply}


# ── API: Stats ────────────────────────────────────────────────────────────────

@app.get("/api/stats")
async def api_stats(user: dict = Depends(require_user)):
    stats = await db.get_post_stats(user_id=user["id"])
    accounts = await db.get_accounts(user_id=user["id"])

    # Post history for chart (last 7 days)
    from database import DB_PATH
    import aiosqlite
    chart_data = []
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        for i in range(6, -1, -1):
            day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            cur = await conn.execute(
                "SELECT COUNT(*) FROM post_log WHERE created_at LIKE ? AND user_id = ?",
                (f"{day}%", user["id"])
            )
            count = (await cur.fetchone())[0]
            chart_data.append({"date": day, "count": count})

    return {**stats, "chart": chart_data, "accounts_count": len(accounts)}


# ── Admin API ─────────────────────────────────────────────────────────────────

@app.get("/api/admin/users")
async def api_admin_users(user: dict = Depends(require_user)):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")
    users = await db.get_all_users()
    return {"users": users}


@app.patch("/api/admin/users/{user_id}")
async def api_admin_update_user(user_id: int, request: Request, user: dict = Depends(require_user)):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")
    data = await request.json()
    allowed = {"plan", "accounts_limit", "is_admin"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if updates:
        await db.update_user(user_id, **updates)
    return {"ok": True}


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    await db.init_db()
    print("[webapp] Database initialized")
    print(f"[webapp] Admin TG ID: {ADMIN_TG_ID or 'not set'}")
