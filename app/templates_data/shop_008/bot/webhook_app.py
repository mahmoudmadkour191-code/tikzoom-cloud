from fastapi import APIRouter, Request, HTTPException
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update

from app.config import settings
from .handlers import router as handlers_router


api_router = APIRouter(prefix="/telegram", tags=["telegram"]) 

bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=None))
dp = Dispatcher()
dp.include_router(handlers_router)


@api_router.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    if settings.webhook_secret:
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != settings.webhook_secret:
            raise HTTPException(status_code=401, detail="invalid secret")
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}


async def setup_webhook() -> None:
    if settings.webhook_url:
        await bot.set_webhook(settings.webhook_url, secret_token=settings.webhook_secret)


async def delete_webhook() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
