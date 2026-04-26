"""
Threads Engagement Module
Replies, comments, likes, reposts, mentions polling.
Note: Threads DM API is NOT publicly available from Meta — DMs cannot be automated.
"""
import aiohttp, asyncio, logging
from typing import Optional

API = "https://graph.threads.net/v1.0"
log = logging.getLogger(__name__)


async def _get(session, url, params):
    async with session.get(url, params=params) as r:
        return await r.json()


async def _post(session, url, data):
    async with session.post(url, data=data) as r:
        return await r.json()


async def list_user_threads(user_id: str, token: str, limit: int = 25):
    async with aiohttp.ClientSession() as s:
        d = await _get(s, f"{API}/{user_id}/threads", {
            "fields": "id,text,timestamp,permalink",
            "limit": limit,
            "access_token": token,
        })
        return d.get("data", [])


async def list_replies(post_id: str, token: str):
    """Top-level replies on a post."""
    async with aiohttp.ClientSession() as s:
        d = await _get(s, f"{API}/{post_id}/replies", {
            "fields": "id,text,username,from,timestamp,hide_status",
            "access_token": token,
        })
        return d.get("data", [])


async def list_conversation(post_id: str, token: str):
    """Full nested conversation tree under a post."""
    async with aiohttp.ClientSession() as s:
        d = await _get(s, f"{API}/{post_id}/conversation", {
            "fields": "id,text,username,from,timestamp,hide_status,replied_to",
            "access_token": token,
        })
        return d.get("data", [])


async def list_mentions(user_id: str, token: str):
    async with aiohttp.ClientSession() as s:
        d = await _get(s, f"{API}/{user_id}/mentions", {
            "fields": "id,text,username,timestamp,permalink",
            "access_token": token,
        })
        return d.get("data", [])


async def reply_to(user_id: str, token: str, text: str, reply_to_id: str):
    """Create a reply post to a given thread/comment id."""
    async with aiohttp.ClientSession() as s:
        create = await _post(s, f"{API}/{user_id}/threads", {
            "media_type": "TEXT",
            "text": text,
            "reply_to_id": reply_to_id,
            "access_token": token,
        })
        if "error" in create:
            return {"success": False, "error": create["error"].get("message", "")}
        cid = create["id"]
        await asyncio.sleep(5)
        pub = await _post(s, f"{API}/{user_id}/threads_publish", {
            "creation_id": cid,
            "access_token": token,
        })
        if "error" in pub:
            return {"success": False, "error": pub["error"].get("message", "")}
        return {"success": True, "thread_id": pub["id"]}


async def hide_reply(reply_id: str, token: str, hide: bool = True):
    """Hide/unhide a reply on your post."""
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{API}/{reply_id}/manage_reply",
                          data={"hide": str(hide).lower(), "access_token": token}) as r:
            return await r.json()


async def get_insights(post_id: str, token: str):
    """Likes / replies / reposts / quotes / views for a post."""
    async with aiohttp.ClientSession() as s:
        d = await _get(s, f"{API}/{post_id}/insights", {
            "metric": "likes,replies,reposts,quotes,views",
            "access_token": token,
        })
        out = {}
        for m in d.get("data", []):
            try:
                out[m["name"]] = m["values"][0]["value"]
            except Exception:
                pass
        return out


async def repost(user_id: str, token: str, source_thread_id: str):
    """Repost an existing thread."""
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{API}/{source_thread_id}/repost",
                          data={"access_token": token}) as r:
            return await r.json()
