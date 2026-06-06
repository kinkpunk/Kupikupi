from typing import Protocol

import httpx


class TelegramDeliveryError(RuntimeError):
    pass


class TelegramMessageClient(Protocol):
    async def send_message(self, *, chat_id: int, text: str) -> None:
        pass


class TelegramBotClient:
    def __init__(self, *, bot_token: str, base_url: str = "https://api.telegram.org") -> None:
        self._bot_token = bot_token
        self._base_url = base_url.rstrip("/")

    async def send_message(self, *, chat_id: int, text: str) -> None:
        url = f"{self._base_url}/bot{self._bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "disable_web_page_preview": True,
                },
            )

        if response.status_code >= 400:
            raise TelegramDeliveryError(
                f"Telegram sendMessage failed with status {response.status_code}."
            )

