from typing import Optional
from pathlib import Path
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from app.models import Item, ItemType
from app.utils.texts import load_texts
from app.config import settings


class DeliveryService:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def deliver(self, chat_id: int, item: Item) -> None:
        texts_all = load_texts()
        texts = texts_all.get("delivery", {})
        main_menu_text = texts_all.get("buttons", {}).get("main_menu", "Главное меню")
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=main_menu_text, callback_data="back:main")]])
        if item.item_type == ItemType.SERVICE:
            # Приоритет: CONTACT_ADMIN из окружения -> поле товара -> фраза по умолчанию
            contact = settings.contact_admin or item.service_admin_contact or "администратору"
            await self.bot.send_message(
                chat_id,
                texts.get("service", "Спасибо за покупку! Чтобы получить услугу — напишите {contact}.").format(contact=contact),
                reply_markup=kb,
            )
            return

        if item.item_type == ItemType.DIGITAL:
            if item.digital_file_path:
                # Пробуем отправить файл как документ: сначала локальный путь, иначе как file_id
                try:
                    file_source = FSInputFile(item.digital_file_path) if Path(item.digital_file_path).is_file() else item.digital_file_path
                    await self.bot.send_document(chat_id, file_source, reply_markup=kb)
                except Exception:
                    await self.bot.send_message(
                        chat_id,
                        texts.get("digital_fallback", "Файл будет отправлен администратором. Спасибо за покупку!"),
                        reply_markup=kb,
                    )
            else:
                # Путь не указан — сообщаем пользователю, что файл пришлёт администратор
                await self.bot.send_message(
                    chat_id,
                    texts.get("digital_fallback", "Файл будет отправлен администратором. Спасибо за покупку!"),
                    reply_markup=kb,
                )
            return

