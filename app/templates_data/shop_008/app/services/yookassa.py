import base64
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional
import ipaddress
from loguru import logger

import httpx

from app.config import settings


class YooKassaClient:
    def __init__(self) -> None:
        self.base_url = "https://api.yookassa.ru/v3/"
        # Basic auth: shopId:secretKey
        basic = f"{settings.yk_shop_id}:{settings.yk_secret_key}".encode("utf-8")
        auth_header = base64.b64encode(basic).decode("utf-8")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=15.0, pool=5.0),
        )

    async def create_payment(
        self,
        amount_minor: int,
        description: str,
        payment_id: str,
        payment_method_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        customer_email: Optional[str] = None,
        idempotence_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        # amount in RUB with 2 decimals using Decimal
        value = (Decimal(amount_minor) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        amount = {"value": str(value), "currency": "RUB"}
        # Нормализуем metadata в строки, как требует API
        norm_metadata: Dict[str, Any] | None = None
        if metadata is not None:
            norm_metadata = {str(k): (str(v) if v is not None else "") for k, v in metadata.items()}

        payload: Dict[str, Any] = {
            "amount": amount,
            "capture": True,
            "description": description,
            "confirmation": {"type": "redirect", "return_url": settings.yk_return_url},
            "metadata": norm_metadata or {"paymentId": payment_id},
        }
        if payment_method_type:
            payload["payment_method_data"] = {"type": payment_method_type}
        # Добавим чек (если задан email) — минимально допустимый по докам
        if customer_email:
            payload["receipt"] = {
                "customer": {"email": customer_email},
                "items": [
                    {
                        "description": (description[:128] if description else "Item"),
                        "amount": amount,
                        "quantity": "1.0",
                        "vat_code": 1,
                    }
                ],
            }
        # Idempotence-Key: используем предоставленный ключ или payment_id
        headers = {"Idempotence-Key": (idempotence_key or payment_id)}
        logger.bind(event="yk.request").info("Создание платежа в ЮKassa")
        resp = await self._client.post("payments", json=payload, headers=headers)
        logger.bind(event="yk.response").info("Ответ ЮKassa: статус={status}", status=resp.status_code)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()

    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        resp = await self._client.get(f"payments/{payment_id}")
        resp.raise_for_status()
        return resp.json()


def verify_webhook_basic(auth_header: Optional[str]) -> bool:
    if not settings.yk_webhook_user or not settings.yk_webhook_password:
        return True  # допускаем без Basic, если не настроены
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        raw = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
        user, pwd = raw.split(":", 1)
        return user == settings.yk_webhook_user and pwd == settings.yk_webhook_password
    except Exception:
        return False


# Диапазоны IP ЮKassa согласно документации
_YK_CIDRS = [
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11/32",
    "77.75.156.35/32",
    "77.75.154.128/25",
    "2a02:5180::/32",
]
_YK_NETWORKS = [ipaddress.ip_network(cidr) for cidr in _YK_CIDRS]


def is_trusted_yookassa_ip(remote_ip: Optional[str]) -> bool:
    if not remote_ip:
        return False
    try:
        ip_obj = ipaddress.ip_address(remote_ip)
    except ValueError:
        return False
    return any(ip_obj in net for net in _YK_NETWORKS)


