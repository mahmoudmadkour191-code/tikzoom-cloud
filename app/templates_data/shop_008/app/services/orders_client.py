import httpx
from typing import Optional

from app.config import settings


class OrdersClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.base_url, headers={"Content-Type": "application/json"})

    async def __aenter__(self) -> "OrdersClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def create_order(self, item_id: int | None, tg_id: int, payment_method: int | None = None, amount_minor: int | None = None) -> str:
        payload = {
            "item_id": item_id,
            "tg_id": tg_id,
        }
        if payment_method is not None:
            payload["payment_method"] = payment_method
        if amount_minor is not None:
            payload["amount_minor"] = amount_minor
        resp = await self._client.post("/orders/", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["payment_url"]

    async def close(self) -> None:
        await self._client.aclose()
