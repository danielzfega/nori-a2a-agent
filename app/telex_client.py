import httpx
from app.config import settings
from loguru import logger

class TelexClient:
    def __init__(self):
        self.base = settings.telex_base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=20.0)

    def _headers(self):
        return {"Authorization": f"Bearer {settings.telex_api_key}", "Content-Type": "application/json"}

    async def send_dm(self, user_id: str, content: str):
        """
        Send a direct message to a user.
        NOTE: adapt this endpoint to match your Telex API.
        """
        url = f"{self.base}/v1/messages"
        payload = {"type": "direct_message", "recipient_id": user_id, "content": content}
        logger.info("Sending DM to %s", user_id)
        r = await self._client.post(url, json=payload, headers=self._headers())
        r.raise_for_status()
        return r.json()

    async def close(self):
        await self._client.aclose()
