import asyncio, aiohttp, os
from aiohttp import web
from threads_api import get_long_lived_token
import database as db

THREADS_APP_ID = os.environ.get("THREADS_APP_ID", "")
THREADS_APP_SECRET = os.environ.get("THREADS_APP_SECRET", "")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "")
SCOPES = "threads_basic,threads_content_publish,threads_manage_replies,threads_manage_insights"

pending_auth = {}

def get_auth_url(state):
    return (f"https://threads.net/oauth/authorize?client_id={THREADS_APP_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPES}&response_type=code&state={state}")

async def handle_callback(request):
    code = request.query.get("code")
    state = request.query.get("state")
    error = request.query.get("error")

    if error:
        return web.Response(text=f"Error: {error}", content_type="text/html")
    if not code or not state:
        return web.Response(text="Error: no code or state", content_type="text/html")

    telegram_user_id = pending_auth.pop(state, None)
    if not telegram_user_id:
        return web.Response(text="Error: unknown state", content_type="text/html")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://graph.threads.net/oauth/access_token",
                data={
                    "client_id": THREADS_APP_ID,
                    "client_secret": THREADS_APP_SECRET,
                    "grant_type": "authorization_code",
                    "redirect_uri": REDIRECT_URI,
                    "code": code
                }
            ) as resp:
                data = await resp.json()

        if "error" in data:
            return web.Response(text=f"Error: {data['error'].get('message', str(data))}", content_type="text/html")

        short_token = data["access_token"]
        user_id = str(data["user_id"])

        long_data = await get_long_lived_token(short_token, THREADS_APP_SECRET)
        long_token = long_data.get("access_token", short_token)

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://graph.threads.net/v1.0/{user_id}",
                params={"fields": "id,username", "access_token": long_token}
            ) as resp:
                profile = await resp.json()

        username = profile.get("username", f"user_{user_id}")
        acc_id = await db.add_account(username, long_token, user_id)

        return web.Response(
            text=f"<h1>✅ Подключено!</h1><p>@{username} (ID: {acc_id})</p>",
            content_type="text/html"
        )
    except Exception as e:
        return web.Response(text=f"Error: {str(e)}", content_type="text/html")

async def start_oauth_server(port=5000):
    app = web.Application()
    app.router.add_get("/callback", handle_callback)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"OAuth server started on port {port}")
    return runner
