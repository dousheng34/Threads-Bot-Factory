"""
OAuth Module — Авторизация аккаунтов Threads через OAuth
Callback обрабатывается через единый веб-сервер в bot.py
"""
import os
import aiohttp
from aiohttp import web
from threads_api import get_long_lived_token
import database as db

THREADS_APP_ID = os.getenv("THREADS_APP_ID", "4354181008180845")
THREADS_APP_SECRET = os.getenv("THREADS_APP_SECRET", "d1fa8ed851c44a6befd21ff050202c9f")
# На Pella: установи REDIRECT_URI = https://<твой-домен.pella.app>/callback
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://209.126.86.32:8080/callback")
SCOPES = "threads_basic,threads_content_publish,threads_manage_replies,threads_manage_insights"

# Хранилище pending авторизаций {state: telegram_user_id}
pending_auth = {}


def get_auth_url(state: str) -> str:
    """Генерация URL для авторизации Threads"""
    return (
        f"https://threads.net/oauth/authorize"
        f"?client_id={THREADS_APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
        f"&response_type=code"
        f"&state={state}"
    )


async def handle_callback(request):
    """Обработка OAuth callback от Threads"""
    code = request.query.get("code")
    state = request.query.get("state")
    error = request.query.get("error")

    if error:
        return web.Response(text=f"❌ Ошибка: {error}", content_type="text/html")

    if not code or not state:
        return web.Response(text="❌ Нет кода или state", content_type="text/html")

    telegram_user_id = pending_auth.pop(state, None)
    if not telegram_user_id:
        return web.Response(text="❌ Неизвестный state", content_type="text/html")

    try:
        # Обмен кода на short-lived token
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://graph.threads.net/oauth/access_token",
                data={
                    "client_id": THREADS_APP_ID,
                    "client_secret": THREADS_APP_SECRET,
                    "grant_type": "authorization_code",
                    "redirect_uri": REDIRECT_URI,
                    "code": code,
                }
            ) as resp:
                data = await resp.json()

        if "error" in data:
            return web.Response(
                text=f"❌ Ошибка: {data['error'].get('message', str(data))}",
                content_type="text/html"
            )

        short_token = data["access_token"]
        user_id = str(data["user_id"])

        # Получаем long-lived token (60 дней)
        long_data = await get_long_lived_token(short_token, THREADS_APP_SECRET)
        long_token = long_data.get("access_token", short_token)

        # Получаем username
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://graph.threads.net/v1.0/{user_id}",
                params={"fields": "id,username", "access_token": long_token}
            ) as resp:
                profile = await resp.json()

        username = profile.get("username", f"user_{user_id}")

        # Сохраняем в БД
        acc_id = await db.add_account(username, long_token, user_id)

        return web.Response(
            text=f"""
            <html>
            <body style="font-family:Arial;text-align:center;padding:50px;background:#1a1a2e;color:white">
            <h1>✅ Аккаунт подключён!</h1>
            <p>👤 @{username}</p>
            <p>🆔 ID: {acc_id}</p>
            <p>Вернитесь в Telegram бот.</p>
            </body></html>
            """,
            content_type="text/html"
        )

    except Exception as e:
        return web.Response(
            text=f"❌ Ошибка: {str(e)}",
            content_type="text/html"
        )
