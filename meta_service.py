import httpx
from loguru import logger

META_API_VERSION = "v20.0"
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"
THREADS_BASE_URL = f"https://graph.threads.net/{META_API_VERSION}"

class MetaService:
    def __init__(self):
        self.client = httpx.AsyncClient()

    async def get_long_lived_token(self, client_id: str, client_secret: str, short_lived_token: str) -> str:
        """Exchange short-lived Meta user access token for a long-lived 60-day token"""
        url = f"{META_BASE_URL}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "fb_exchange_token": short_lived_token
        }
        try:
            r = await self.client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            return data.get("access_token", short_lived_token)
        except Exception as e:
            logger.error(f"[meta] Token exchange failed: {e}")
            return short_lived_token

    # ── Threads API ────────────────────────────────────────────────────────

    async def get_threads_profile(self, access_token: str) -> dict:
        """Fetch Threads user profile info"""
        url = f"https://graph.threads.net/me"
        params = {
            "fields": "id,username,threads_profile_picture_url",
            "access_token": access_token
        }
        try:
            r = await self.client.get(url, params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"[threads] Fetch profile failed: {e}")
            return {}

    async def publish_threads_post(self, threads_user_id: str, access_token: str, text: str, media_url: str = None) -> dict:
        """Publish post or thread onto Threads"""
        try:
            # Step 1: Create media container
            container_url = f"https://graph.threads.net/{threads_user_id}/threads"
            payload = {
                "media_type": "TEXT",
                "text": text,
                "access_token": access_token
            }
            if media_url:
                payload["media_type"] = "IMAGE"
                payload["image_url"] = media_url

            r = await self.client.post(container_url, data=payload)
            r.raise_for_status()
            creation_id = r.json().get("id")

            if not creation_id:
                return {"success": False, "error": "No creation_id returned"}

            # Step 2: Publish container
            publish_url = f"https://graph.threads.net/{threads_user_id}/threads_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": access_token
            }
            r_pub = await self.client.post(publish_url, data=publish_payload)
            r_pub.raise_for_status()
            thread_id = r_pub.json().get("id")

            return {"success": True, "thread_id": thread_id}
        except Exception as e:
            logger.error(f"[threads] Publish failed: {e}")
            return {"success": False, "error": str(e)}

    async def fetch_threads_comments(self, threads_user_id: str, access_token: str) -> list:
        """Fetch comments and replies on user's threads"""
        url = f"https://graph.threads.net/{threads_user_id}/replies"
        params = {"access_token": access_token}
        try:
            r = await self.client.get(url, params=params)
            r.raise_for_status()
            return r.json().get("data", [])
        except Exception as e:
            logger.error(f"[threads] Fetch replies failed: {e}")
            return []

    async def reply_to_threads_comment(self, access_token: str, parent_id: str, reply_text: str) -> dict:
        """Reply to a comment on Threads"""
        # Note: Meta Threads API uses /threads endpoint on the user or parent node
        url = f"https://graph.threads.net/{parent_id}/replies"
        payload = {
            "text": reply_text,
            "access_token": access_token
        }
        try:
            r = await self.client.post(url, data=payload)
            r.raise_for_status()
            return {"success": True, "reply_id": r.json().get("id")}
        except Exception as e:
            logger.error(f"[threads] Reply failed: {e}")
            return {"success": False, "error": str(e)}

    # ── Instagram Graph API ────────────────────────────────────────────────

    async def get_instagram_business_account(self, page_id: str, access_token: str) -> str:
        """Get connected Instagram business account ID from Facebook Page ID"""
        url = f"{META_BASE_URL}/{page_id}"
        params = {
            "fields": "instagram_business_account",
            "access_token": access_token
        }
        try:
            r = await self.client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            return data.get("instagram_business_account", {}).get("id")
        except Exception as e:
            logger.error(f"[instagram] Fetch biz account failed: {e}")
            return ""

    async def publish_instagram_post(self, instagram_biz_id: str, access_token: str, caption: str, media_url: str) -> dict:
        """Publish post (photo/video) on Instagram Business profile"""
        try:
            # Step 1: Create media container
            container_url = f"{META_BASE_URL}/{instagram_biz_id}/media"
            payload = {
                "image_url": media_url,
                "caption": caption,
                "access_token": access_token
            }
            r = await self.client.post(container_url, data=payload)
            r.raise_for_status()
            creation_id = r.json().get("id")

            if not creation_id:
                return {"success": False, "error": "No creation_id returned"}

            # Step 2: Publish container
            publish_url = f"{META_BASE_URL}/{instagram_biz_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": access_token
            }
            r_pub = await self.client.post(publish_url, data=publish_payload)
            r_pub.raise_for_status()
            ig_post_id = r_pub.json().get("id")

            return {"success": True, "post_id": ig_post_id}
        except Exception as e:
            logger.error(f"[instagram] Publish failed: {e}")
            return {"success": False, "error": str(e)}

    async def fetch_instagram_comments(self, media_id: str, access_token: str) -> list:
        """Fetch comments for a media post on Instagram"""
        url = f"{META_BASE_URL}/{media_id}/comments"
        params = {
            "fields": "id,text,username,timestamp,from",
            "access_token": access_token
        }
        try:
            r = await self.client.get(url, params=params)
            r.raise_for_status()
            return r.json().get("data", [])
        except Exception as e:
            logger.error(f"[instagram] Fetch comments failed: {e}")
            return []

    async def reply_to_instagram_comment(self, access_token: str, comment_id: str, reply_text: str) -> dict:
        """Reply to an Instagram comment"""
        url = f"{META_BASE_URL}/{comment_id}/replies"
        payload = {
            "message": reply_text,
            "access_token": access_token
        }
        try:
            r = await self.client.post(url, data=payload)
            r.raise_for_status()
            return {"success": True, "reply_id": r.json().get("id")}
        except Exception as e:
            logger.error(f"[instagram] Reply failed: {e}")
            return {"success": False, "error": str(e)}

    async def send_instagram_dm(self, access_token: str, recipient_id: str, message_text: str) -> dict:
        """Send Direct Message (DM) to Instagram user via page access token"""
        url = f"{META_BASE_URL}/me/messages"
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text},
            "access_token": access_token
        }
        try:
            r = await self.client.post(url, json=payload)
            r.raise_for_status()
            return {"success": True, "message_id": r.json().get("message_id")}
        except Exception as e:
            logger.error(f"[instagram] DM failed: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        await self.client.aclose()

meta_service = MetaService()
