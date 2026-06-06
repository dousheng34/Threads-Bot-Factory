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
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

import database as db
from threads_api import process_spintax, publish_thread, get_user_profile
import ai_engine
from oauth import router as oauth_router

app = FastAPI(title="Threads Bot Factory", version="2.0")
app.include_router(oauth_router)


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_TG_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "30"))



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

@app.get("/")
async def index(request: Request):
    return RedirectResponse("/dashboard")


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





# ── API: Accounts ─────────────────────────────────────────────────────────────

@app.get("/api/accounts")
async def api_accounts(user: dict = Depends(require_user)):
    accounts = await db.get_social_accounts(user_id=user["id"])
    return {"accounts": accounts}


@app.post("/api/accounts/add")
async def api_add_account(
    request: Request,
    user: dict = Depends(require_user)
):
    data = await request.json()
    platform = data.get("platform", "threads").strip()
    username = data.get("username", "").strip()
    token = data.get("access_token", "").strip()
    threads_user_id = data.get("threads_user_id", "").strip()

    if not username or not token:
        raise HTTPException(400, "username and access_token required")

    # Check plan limits
    existing = await db.get_social_accounts(user_id=user["id"])
    if len(existing) >= user["accounts_limit"]:
        raise HTTPException(403, f"Лимит аккаунтов: {user['accounts_limit']}. Нужен PRO тариф.")

    acc_id = await db.add_social_account(
        user_id=user["id"],
        platform=platform,
        platform_user_id=threads_user_id,
        username=username,
        access_token=token
    )
    return {"ok": True, "account_id": acc_id}


@app.delete("/api/accounts/{account_id}")
async def api_delete_account(account_id: int, user: dict = Depends(require_user)):
    acc = await db.get_social_account(account_id)
    if not acc or acc.get("user_id") != user["id"]:
        raise HTTPException(404, "Account not found")
    await db.delete_social_account(account_id)
    return {"ok": True}


@app.patch("/api/accounts/{account_id}")
async def api_update_account(account_id: int, request: Request, user: dict = Depends(require_user)):
    acc = await db.get_social_account(account_id)
    if not acc or acc.get("user_id") != user["id"]:
        raise HTTPException(404, "Account not found")
    data = await request.json()
    allowed = {"status", "username", "access_token", "refresh_token", "token_expires_at"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if updates:
        await db.update_social_account(account_id, **updates)
    return {"ok": True}


# ── API: Post ────────────────────────────────────────────────────────────

@app.post("/api/post/adapt")
async def api_adapt_post(request: Request, user: dict = Depends(require_user)):
    data = await request.json()
    content = data.get("content", "").strip()
    if not content:
        raise HTTPException(400, "content required")
    adapted = await ai_engine.adapt_content(content)
    return {"adapted": adapted}


@app.post("/api/post/quick")
async def api_quick_post(request: Request, user: dict = Depends(require_user)):
    data = await request.json()
    account_ids = data.get("account_ids", [])
    content_config = data.get("content")
    media_url = data.get("media_url")
    
    if not account_ids or not content_config:
        raise HTTPException(400, "account_ids and content config required")
        
    results = []
    from meta_service import meta_service
    from whatsapp_service import whatsapp_service
    
    for acc_id in account_ids:
        acc = await db.get_social_account(acc_id)
        if not acc or acc.get("user_id") != user["id"]:
            continue
            
        platform = acc["platform"]
        success = False
        ext_id = None
        err_msg = None
        published_text = ""
        
        if platform == "threads":
            threads_data = content_config.get("threads", [])
            text = threads_data[0] if isinstance(threads_data, list) and threads_data else str(threads_data)
            res = await meta_service.publish_threads_post(acc["threads_user_id"], acc["access_token"], text, media_url)
            success = res.get("success", False)
            ext_id = res.get("thread_id")
            err_msg = res.get("error")
            published_text = text
                
        elif platform == "instagram":
            ig_data = content_config.get("instagram", {})
            caption = ig_data.get("caption", "")
            tags = " ".join(ig_data.get("hashtags", []))
            full_caption = f"{caption}\n\n{tags}".strip()
            target_media = media_url or "https://picsum.photos/800/800"
            res = await meta_service.publish_instagram_post(acc["threads_user_id"], acc["access_token"], full_caption, target_media)
            success = res.get("success", False)
            ext_id = res.get("post_id")
            err_msg = res.get("error")
            published_text = full_caption
            
        elif platform == "whatsapp":
            wa_data = content_config.get("whatsapp", {})
            text = wa_data.get("text", "")
            cta = wa_data.get("cta", "")
            full_msg = f"{text}\n\n{cta}".strip()
            res = await whatsapp_service.send_whatsapp_message(
                phone_number_id=acc["threads_user_id"],
                access_token=acc["access_token"],
                recipient_phone=acc["username"],
                message_text=full_msg
            )
            success = res.get("success", False)
            ext_id = res.get("message_id")
            err_msg = res.get("error")
            published_text = full_msg
            
        status_str = "success" if success else "error"
        await db.log_post(
            account_id=acc_id,
            content=published_text,
            status=status_str,
            thread_id=ext_id,
            error=err_msg,
            user_id=user["id"]
        )
        
        results.append({
            "account_id": acc_id,
            "platform": platform,
            "success": success,
            "post_id": ext_id,
            "error": err_msg
        })
        
    return {"results": results}


@app.post("/api/post/schedule")
async def api_schedule_post(request: Request, user: dict = Depends(require_user)):
    data = await request.json()
    account_ids = data.get("account_ids", [])
    content_data = data.get("content")
    scheduled_at = data.get("scheduled_at", "")
    use_spintax = data.get("use_spintax", False)

    if not account_ids or not content_data or not scheduled_at:
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


# ── LeadGen API ──────────────────────────────────────────────────────────────

@app.get("/api/leadgen/rules")
async def api_get_rules(user: dict = Depends(require_user)):
    rules = await db.get_auto_reply_configs(user_id=user["id"])
    return {"rules": rules}


@app.post("/api/leadgen/rules")
async def api_create_rule(request: Request, user: dict = Depends(require_user)):
    data = await request.json()
    social_account_id = data.get("social_account_id")
    trigger_keyword = data.get("trigger_keyword", "").strip()
    response_text = data.get("response_text", "").strip()
    match_type = data.get("match_type", "exact").strip()
    response_type = data.get("response_type", "dm").strip()
    guide_file_url = data.get("guide_file_url", "").strip() or None
    
    if not trigger_keyword or not response_text:
        raise HTTPException(400, "trigger_keyword and response_text are required")
        
    rule_id = await db.add_auto_reply_config(
        user_id=user["id"],
        social_account_id=int(social_account_id) if social_account_id else None,
        trigger_keyword=trigger_keyword,
        response_text=response_text,
        response_type=response_type,
        match_type=match_type,
        guide_file_url=guide_file_url
    )
    return {"ok": True, "rule_id": rule_id}


@app.patch("/api/leadgen/rules/{rule_id}")
async def api_update_rule(rule_id: int, request: Request, user: dict = Depends(require_user)):
    # Verify owner
    configs = await db.get_auto_reply_configs(user["id"])
    if not any(c["id"] == rule_id for c in configs):
        raise HTTPException(404, "Rule not found")
        
    data = await request.json()
    allowed = {"trigger_keyword", "response_text", "match_type", "response_type", "guide_file_url", "is_active"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if "social_account_id" in data:
        updates["social_account_id"] = int(data["social_account_id"]) if data["social_account_id"] else None
        
    if updates:
        await db.update_auto_reply_config(rule_id, **updates)
    return {"ok": True}


@app.delete("/api/leadgen/rules/{rule_id}")
async def api_delete_rule(rule_id: int, user: dict = Depends(require_user)):
    # Verify owner
    configs = await db.get_auto_reply_configs(user["id"])
    if not any(c["id"] == rule_id for c in configs):
        raise HTTPException(404, "Rule not found")
        
    await db.delete_auto_reply_config(rule_id)
    return {"ok": True}


@app.get("/api/leadgen/leads")
async def api_get_leads(user: dict = Depends(require_user)):
    leads = await db.get_lead_logs(user_id=user["id"])
    return {"leads": leads}


# ── WhatsApp Webhook ─────────────────────────────────────────────────────────

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_secure_whatsapp_token_123")

@app.get("/api/webhook/whatsapp")
async def verify_whatsapp_webhook(request: Request):
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        print("[whatsapp] Webhook verified!")
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(challenge)
    else:
        raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/api/webhook/whatsapp")
async def listen_whatsapp_webhook(request: Request):
    try:
        body = await request.json()
        print(f"[whatsapp] Webhook payload: {json.dumps(body)}")
        
        entry = body.get("entry", [])
        if not entry:
            return {"status": "ignored"}
            
        changes = entry[0].get("changes", [])
        if not changes:
            return {"status": "ignored"}
            
        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        
        if messages:
            msg = messages[0]
            from_phone = msg.get("from")
            msg_body = msg.get("text", {}).get("body", "").strip()
            msg_id = msg.get("id")
            
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id")
            
            accounts = await db.get_social_accounts(platform="whatsapp")
            wa_account = None
            for acc in accounts:
                if acc["threads_user_id"] == phone_number_id:
                    wa_account = acc
                    break
                    
            if wa_account:
                conv = await db.get_or_create_conversation(
                    social_account_id=int(wa_account["id"]),
                    platform="whatsapp",
                    external_thread_id=from_phone,
                    external_user_id=from_phone,
                    external_username=from_phone
                )
                
                db_msg_id = await db.add_message(
                    conversation_id=int(conv["id"]),
                    external_message_id=msg_id,
                    direction="inbound",
                    message_text=msg_body,
                    sentiment="neutral"
                )

                # Dispatch Telegram notification to owner
                from bot import bot
                user = await db.get_user(wa_account["user_id"])
                if bot and user:
                    try:
                        await bot.send_message(
                            chat_id=user["telegram_id"],
                            text=(
                                f"💬 WhatsApp | @{from_phone}:\n"
                                f"{msg_body}\n\n"
                                f"Ответьте на это сообщение для отправки ответа.\n"
                                f"[ID: c_{conv['id']}]"
                            )
                        )
                    except Exception as bot_err:
                        print(f"[bot] Failed to notify owner: {bot_err}")
                
                # Check for keyword autoresponders
                configs = await db.get_auto_reply_configs(user_id=int(wa_account["user_id"]))
                for cfg in configs:
                    trigger = cfg["trigger_keyword"].lower()
                    match_type = cfg["match_type"]
                    
                    is_match = False
                    if match_type == "exact" and msg_body.lower() == trigger:
                        is_match = True
                    elif match_type == "contains" and trigger in msg_body.lower():
                        is_match = True
                        
                    if is_match and cfg["is_active"]:
                        from whatsapp_service import whatsapp_service
                        reply_text = cfg["response_text"]
                        
                        resp = await whatsapp_service.send_whatsapp_message(
                            phone_number_id=phone_number_id,
                            access_token=wa_account["access_token"],
                            recipient_phone=from_phone,
                            message_text=reply_text
                        )
                        
                        status = "sent" if resp.get("success") else "failed"
                        await db.log_lead(
                            user_id=int(wa_account["user_id"]),
                            auto_reply_id=int(cfg["id"]),
                            conversation_id=int(conv["id"]),
                            recipient_external_id=from_phone,
                            status=status
                        )
                        
                        # Log outbound message
                        await db.add_message(
                            conversation_id=int(conv["id"]),
                            external_message_id=resp.get("message_id") or f"out_{int(datetime.now().timestamp())}",
                            direction="outbound",
                            message_text=reply_text
                        )
                        
        return {"status": "ok"}
    except Exception as e:
        print(f"[whatsapp] Webhook listener error: {e}")
        return {"status": "error", "detail": str(e)}


# ── Meta Webhooks ────────────────────────────────────────────────────────────

META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "my_secure_meta_token_123")

@app.get("/api/webhook/meta")
async def verify_meta_webhook(request: Request):
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        print("[meta] Webhook verified!")
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(challenge)
    else:
        raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/api/webhook/meta")
async def listen_meta_webhook(request: Request):
    try:
        body = await request.json()
        print(f"[meta] Webhook payload: {json.dumps(body)}")
        
        obj_type = body.get("object", "")
        entry = body.get("entry", [])
        if not entry:
            return {"status": "ignored"}
            
        changes = entry[0].get("changes", [])
        if not changes:
            return {"status": "ignored"}
            
        value = changes[0].get("value", {})
        comment_id = value.get("id")
        comment_text = value.get("text")
        
        platform = "threads" if obj_type == "threads" else "instagram"
        
        if comment_id and comment_text:
            from_user = value.get("from", {})
            from_username = from_user.get("username", "unknown")
            from_id = from_user.get("id")
            
            meta_account_id = entry[0].get("id")
            accounts = await db.get_social_accounts(platform=platform)
            target_acc = None
            for acc in accounts:
                if acc["threads_user_id"] == meta_account_id:
                    target_acc = acc
                    break
                    
            if target_acc:
                conv = await db.get_or_create_conversation(
                    social_account_id=int(target_acc["id"]),
                    platform=platform,
                    external_thread_id=comment_id,
                    external_user_id=from_id,
                    external_username=from_username
                )
                
                await db.add_message(
                    conversation_id=int(conv["id"]),
                    external_message_id=comment_id,
                    direction="inbound",
                    message_text=comment_text,
                    sentiment="neutral"
                )
                
                from bot import bot
                user = await db.get_user(target_acc["user_id"])
                if bot and user:
                    try:
                        plat_label = "Threads" if platform == "threads" else "Instagram"
                        await bot.send_message(
                            chat_id=user["telegram_id"],
                            text=(
                                f"💬 {plat_label} | @{from_username}:\n"
                                f"{comment_text}\n\n"
                                f"Ответьте на это сообщение для отправки ответа.\n"
                                f"[ID: c_{conv['id']}]"
                            )
                        )
                    except Exception as bot_err:
                        print(f"[bot] Failed to notify owner via telegram: {bot_err}")
                        
        return {"status": "ok"}
    except Exception as e:
        print(f"[meta] Webhook error: {e}")
        return {"status": "error", "detail": str(e)}


# ── Analytics API ─────────────────────────────────────────────────────────────

@app.get("/api/analytics/snapshots")
async def api_analytics_snapshots(user: dict = Depends(require_user)):
    accounts = await db.get_social_accounts(user_id=user["id"])
    all_snapshots = {}
    for acc in accounts:
        snaps = await db.get_analytics_snapshots(acc["id"], limit=10)
        # Sort oldest first for frontend chart progression
        all_snapshots[acc["username"]] = sorted(snaps, key=lambda x: x["snapshot_date"])
    return {"snapshots": all_snapshots}


@app.get("/api/analytics/report")
async def api_analytics_report(user: dict = Depends(require_user)):
    from report_generator import generate_pdf_report
    pdf_buffer = await generate_pdf_report(user["id"])
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=smm_analytics_report.pdf"}
    )


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    await db.init_db()
    print("[webapp] Database initialized")
    print(f"[webapp] Admin TG ID: {ADMIN_TG_ID or 'not set'}")

