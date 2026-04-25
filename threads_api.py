"""
Threads API Module
"""
import aiohttp
import asyncio
import random
import re

API = "https://graph.threads.net/v1.0"


def process_spintax(text: str) -> str:
    pattern = r'\{([^{}]+)\}'
    def repl(m):
        return random.choice(m.group(1).split('|'))
    result = text
    while re.search(pattern, result):
        result = re.sub(pattern, repl, result)
    return result


async def publish_thread(user_id, token, text, reply_to_id=None, image_url=None):
    try:
        async with aiohttp.ClientSession() as s:
            payload = {
                "media_type": "IMAGE" if image_url else "TEXT",
                "text": text,
                "access_token": token
            }
            if image_url:
                payload["image_url"] = image_url
            if reply_to_id:
                payload["reply_to_id"] = reply_to_id

            async with s.post(f"{API}/{user_id}/threads", data=payload) as r:
                d = await r.json()
                if "error" in d:
                    return {"success": False, "error": d["error"].get("message", "")}
                cid = d["id"]

            await asyncio.sleep(5 if not image_url else 30)

            async with s.post(f"{API}/{user_id}/threads_publish", data={"creation_id": cid, "access_token": token}) as r:
                d = await r.json()
                if "error" in d:
                    return {"success": False, "error": d["error"].get("message", "")}
                return {"success": True, "thread_id": d["id"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_user_profile(user_id, token):
    async with aiohttp.ClientSession() as s:
        async with s.get(f"{API}/{user_id}", params={"fields": "id,username", "access_token": token}) as r:
            return await r.json()


async def get_long_lived_token(short_token, app_secret):
    async with aiohttp.ClientSession() as s:
        async with s.get(
            "https://graph.threads.net/access_token",
            params={"grant_type": "th_exchange_token", "client_secret": app_secret, "access_token": short_token}
        ) as r:
            return await r.json()


async def refresh_token(token):
    async with aiohttp.ClientSession() as s:
        async with s.get(
            "https://graph.threads.net/refresh_access_token",
            params={"grant_type": "th_refresh_token", "access_token": token}
        ) as r:
            return await r.json()


async def get_publishing_limit(user_id, token):
    async with aiohttp.ClientSession() as s:
        async with s.get(
            f"{API}/{user_id}/threads_publishing_limit",
            params={"fields": "quota_usage,config", "access_token": token}
        ) as r:
            return await r.json()
