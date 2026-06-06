import httpx
from loguru import logger

META_API_VERSION = "v20.0"
WHATSAPP_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

class WhatsAppService:
    def __init__(self):
        self.client = httpx.AsyncClient()

    async def send_whatsapp_message(self, phone_number_id: str, access_token: str, 
                                    recipient_phone: str, message_text: str) -> dict:
        """Send freeform text message to a user on WhatsApp (Cloud API)"""
        url = f"{WHATSAPP_BASE_URL}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": message_text
            }
        }
        try:
            r = await self.client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            return {"success": True, "message_id": r.json().get("messages", [{}])[0].get("id")}
        except Exception as e:
            logger.error(f"[whatsapp] Text message failed: {e}")
            return {"success": False, "error": str(e)}

    async def send_whatsapp_template(self, phone_number_id: str, access_token: str, 
                                     recipient_phone: str, template_name: str, 
                                     language_code: str = "ru", components: list = None) -> dict:
        """Send a pre-approved template message (required to open conversation with user)"""
        url = f"{WHATSAPP_BASE_URL}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        if components:
            payload["template"]["components"] = components

        try:
            r = await self.client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            return {"success": True, "message_id": r.json().get("messages", [{}])[0].get("id")}
        except Exception as e:
            logger.error(f"[whatsapp] Template message failed: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        await self.client.aclose()

whatsapp_service = WhatsAppService()
