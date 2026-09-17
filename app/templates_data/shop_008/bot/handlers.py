import logging
logger = logging.getLogger("shopbot")
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from pathlib import Path
import contextlib
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func

from app.utils.texts import load_texts
from .keyboards import main_menu_kb, back_kb, item_card_kb, payment_method_kb, items_list_kb, main_menu_only_kb, payment_link_kb, donate_amounts_kb, admin_menu_kb
from app.db.session import AsyncSessionLocal
from app.models import Item, ItemType, User, Purchase
from app.config import settings
from app.services.orders_client import OrdersClient
from app.services.yookassa import YooKassaClient

router = Router()


class DonateStates(StatesGroup):
    waiting_for_amount = State()


class AdminInvoiceStates(StatesGroup):
    waiting_for_description = State()
    waiting_for_amount = State()


def _is_admin_user(tg_id: int | None, username: str | None) -> bool:
    try:
        if settings.admin_chat_id and tg_id is not None:
            if str(tg_id) == str(settings.admin_chat_id):
                return True
    except Exception:
        pass
    if settings.admin_tg_username and username:
        return username.lstrip('@').lower() == settings.admin_tg_username.lstrip('@').lower()
    return False


@router.message(F.text == "/start")
async def start_handler(message: Message) -> None:
    texts = load_texts()

    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.tg_id == message.from_user.id))).scalar_one_or_none()
        if not u:
            u = User(tg_id=message.from_user.id, username=message.from_user.username or None)
            db.add(u)
            await db.flush()
            total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
            if settings.admin_chat_id:
                try:
                    username = f"@{message.from_user.username}" if message.from_user.username else "—"
                    text = (
                        "✅ Новый пользователь "
                        f"{message.from_user.full_name}\n"
                        f"Username: {username}\n"
                        f"ID: {message.from_user.id}\n"
                        f"Всего: {total}"
                    )
                    await message.bot.send_message(int(settings.admin_chat_id), text)
                except Exception:
                    pass
        else:
            if (message.from_user.username or None) != u.username:
                u.username = message.from_user.username or None
        await db.commit()

    # Отправляем главное меню с картинкой если есть
    try:
        if "image" in texts["main_menu"]:
            photo = FSInputFile(texts["main_menu"]["image"])
            await message.answer_photo(
                photo=photo,
                caption=texts["main_menu"]["title"],
                parse_mode="Markdown",
                reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(message.from_user.id, message.from_user.username))
            )
        else:
            await message.answer(texts["main_menu"]["title"], parse_mode="Markdown", reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(message.from_user.id, message.from_user.username)))
    except FileNotFoundError:
        # Если файл не найден, отправляем без картинки
        await message.answer(texts["main_menu"]["title"], reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(message.from_user.id, message.from_user.username)))


@router.message(F.text.startswith("/"))
async def quick_menu_commands(message: Message) -> None:
    cmd = (message.text or "").strip().lstrip("/").lower()
    if cmd == "projects":
        await list_items(message, ItemType.DIGITAL, section="projects", page=1)
        return
    # Солобот модули удалены
    if cmd == "services":
        await list_items(message, ItemType.SERVICE, section="services", page=1)
        return
    if cmd in ("buylist", "purchased", "my"):
        texts = load_texts()
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.tg_id == message.from_user.id))).scalar_one_or_none()
            if not user:
                await message.answer(texts.get("empty", {}).get("purchased", "У вас нет купленных проектов."))
                return
            purchases = (await db.execute(select(Purchase).where(Purchase.user_id == user.id))).scalars().all()
            if not purchases:
                await message.answer(texts.get("empty", {}).get("purchased", "У вас нет купленных проектов."))
                return
            item_ids = [p.item_id for p in purchases if p.item_id is not None]
            items = (await db.execute(select(Item).where(Item.id.in_(item_ids)))).scalars().all()
        kb = []
        for it in items:
            kb.append([InlineKeyboardButton(text=it.title, callback_data=f"item:{it.id}:{it.item_type.value}")])
        kb.append([InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="back:main")])
        title = texts["main_menu"].get("purchased_title", "Ваши купленные проекты:")
        image_path = texts["main_menu"].get("images", {}).get("purchased")
        if image_path and Path(image_path).is_file():
            photo = FSInputFile(image_path)
            await message.answer_photo(photo=photo, caption=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        else:
            await message.answer(text=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    if cmd in ("donat", "donate"):
        texts = load_texts()
        donate_image = texts.get("donate", {}).get("image")
        image_exists = bool(donate_image and Path(donate_image).is_file())
        if image_exists:
            photo = FSInputFile(donate_image)
            await message.answer_photo(photo=photo, caption="Выберите сумму доната:", reply_markup=donate_amounts_kb())
        else:
            await message.answer(text="Выберите сумму доната:", reply_markup=donate_amounts_kb())
        return


# Новый обработчик для inline-кнопок главного меню
@router.callback_query(F.data.startswith("menu:"))
async def main_menu_callback(call: CallbackQuery) -> None:
    texts = load_texts()
    data = call.data.split(":", 1)[1]

    # Маппинг для определения типа элементов и секции
    section_mapping = {
        "projects": (ItemType.DIGITAL, "projects"),
        "services": (ItemType.SERVICE, "services"),
    }

    if data in section_mapping:
        item_type, section = section_mapping[data]
        await list_items(call.message, item_type, section=section, call=call, page=1)
        await call.answer()
        return
    if data == "admin":
        # Доступ только администратору
        if not _is_admin_user(call.from_user.id, call.from_user.username):
            await call.answer("Недоступно", show_alert=True)
            return
        admin_text = load_texts().get("admin", {}).get("title", "Администрирование")
        try:
            if call.message.photo:
                await call.message.edit_caption(caption=admin_text, reply_markup=admin_menu_kb())
            else:
                await call.message.edit_text(text=admin_text, reply_markup=admin_menu_kb())
        except Exception:
            await call.message.answer(admin_text, reply_markup=admin_menu_kb())
            with contextlib.suppress(Exception):
                await call.message.delete()
        await call.answer()
        return


    if data == "donate":
        donate_image = load_texts().get("donate", {}).get("image")
        image_exists = bool(donate_image and Path(donate_image).is_file())
        try:
            if call.message.photo:
                if image_exists:
                    photo = FSInputFile(donate_image)
                    await call.message.edit_media(
                        media=InputMediaPhoto(media=photo, caption="Выберите сумму доната:"),
                        reply_markup=donate_amounts_kb()
                    )
                else:
                    await call.message.edit_caption(caption="Выберите сумму доната:", reply_markup=donate_amounts_kb())
            else:
                if image_exists:
                    photo = FSInputFile(donate_image)
                    await call.message.answer_photo(photo=photo, caption="Выберите сумму доната:", reply_markup=donate_amounts_kb())
                    await call.message.delete()
                else:
                    await call.message.edit_text(text="Выберите сумму доната:", reply_markup=donate_amounts_kb())
        except Exception:
            await call.message.answer(text="Выберите сумму доната:", reply_markup=donate_amounts_kb())
            with contextlib.suppress(Exception):
                await call.message.delete()
        await call.answer()
        return

    # Пагинация списков через callback вида list:<type>:<page>
    if data.startswith("list:"):
        _, type_str, page_str = data.split(":", 2)
        page_num = int(page_str) if page_str.isdigit() else 1
        mapping = {
            "digital": (ItemType.DIGITAL, "projects"),
            "service": (ItemType.SERVICE, "services"),
        }
        if type_str in mapping:
            itype, section = mapping[type_str]
            await list_items(call.message, itype, section=section, call=call, page=page_num)
        await call.answer()
        return

    if data == "purchased":
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
            empty_text = texts.get("empty", {}).get("purchased", "У вас нет купленных проектов.")
            if not user:
                await call.answer(empty_text, show_alert=True)
                return
            purchases = (await db.execute(select(Purchase).where(Purchase.user_id == user.id))).scalars().all()
            if not purchases:
                await call.answer(empty_text, show_alert=True)
                return
            # Получаем товары по id
            item_ids = [p.item_id for p in purchases if p.item_id is not None]
            items = (await db.execute(select(Item).where(Item.id.in_(item_ids)))).scalars().all()
            # Формируем клавиатуру
            kb = []
            for item in items:
                kb.append([InlineKeyboardButton(text=item.title, callback_data=f"item:{item.id}:{item.item_type.value}")])
            kb.append([InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="back:main")])

            title = texts["main_menu"].get("purchased_title", "Ваши купленные проекты:")
            image_path = texts["main_menu"].get("images", {}).get("purchased")
            try:
                if call.message.photo:
                    if image_path and Path(image_path).is_file():
                        photo = FSInputFile(image_path)
                        await call.message.edit_media(
                            media=InputMediaPhoto(media=photo, caption=title),
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
                        )
                    else:
                        await call.message.edit_caption(caption=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
                else:
                    if image_path and Path(image_path).is_file():
                        photo = FSInputFile(image_path)
                        await call.message.answer_photo(photo=photo, caption=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
                        await call.message.delete()
                    else:
                        await call.message.edit_text(text=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            except Exception:
                await call.message.answer(text=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
                with contextlib.suppress(Exception):
                    await call.message.delete()
            await call.answer()
        return


# Пагинация списков (стрелки), когда callback не начинается с "menu:"
@router.callback_query(F.data.startswith("list:"))
async def list_pagination(call: CallbackQuery) -> None:
    try:
        _, type_str, page_str = call.data.split(":", 2)
        page_num = int(page_str) if page_str.isdigit() else 1
    except Exception:
        page_num = 1
        type_str = "digital"
    mapping = {
        "digital": (ItemType.DIGITAL, "projects"),
        "service": (ItemType.SERVICE, "services"),
    }
    if type_str in mapping:
        itype, section = mapping[type_str]
        await list_items(call.message, itype, section=section, call=call, page=page_num)
    await call.answer()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(call: CallbackQuery) -> None:
    _, item_id = call.data.split(":", 1)
    await call.message.edit_reply_markup(reply_markup=payment_method_kb(int(item_id)))
    await call.answer()


@router.callback_query(F.data.startswith("buy_one:"))
async def cb_buy_one(call: CallbackQuery, state: FSMContext) -> None:
    _, item_id = call.data.split(":")
    item_id_int = int(item_id)
    async with OrdersClient() as client:
        try:
            url = await client.create_order(item_id_int, call.from_user.id)
            try:
                await call.message.edit_reply_markup(reply_markup=payment_link_kb(url))
            except Exception:
                # Фолбэк: пытаемся отредактировать подпись/текст, иначе отправим новое сообщение
                try:
                    if call.message.photo:
                        await call.message.edit_caption(caption="Перейдите к оплате:", reply_markup=payment_link_kb(url))
                    else:
                        await call.message.edit_text("Перейдите к оплате:", reply_markup=payment_link_kb(url))
                except Exception:
                    await call.message.answer("Ссылка на оплату:", reply_markup=payment_link_kb(url))
        except Exception:
            await call.message.answer("Не удалось создать заказ. Попробуйте позже.")
    await call.answer()


@router.callback_query(F.data.startswith("buy_direct:"))
async def cb_buy_direct(call: CallbackQuery, state: FSMContext) -> None:
    _, item_id, _ = call.data.split(":")
    item_id_int = int(item_id)
    async with OrdersClient() as client:
        try:
            url = await client.create_order(item_id_int, call.from_user.id)
            try:
                await call.message.edit_reply_markup(reply_markup=payment_link_kb(url))
            except Exception:
                try:
                    if call.message.photo:
                        await call.message.edit_caption(caption="Перейдите к оплате:", reply_markup=payment_link_kb(url))
                    else:
                        await call.message.edit_text("Перейдите к оплате:", reply_markup=payment_link_kb(url))
                except Exception:
                    await call.message.answer("Ссылка на оплату:", reply_markup=payment_link_kb(url))
        except Exception:
            await call.message.answer("Не удалось создать заказ. Попробуйте позже.")
    await call.answer()


@router.callback_query(F.data.startswith("back:"))
async def cb_back(call: CallbackQuery) -> None:
    parts = call.data.split(":")
    action = parts[1]
    item_type = parts[2] if len(parts) > 2 else None
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
    texts = load_texts()
    
    if action == "list" and item_type:
        # Преобразуем строковый тип в ItemType
        item_type_mapping = {
            "digital": ItemType.DIGITAL,
            "service": ItemType.SERVICE,
        }
        section_mapping = {
            "digital": "projects",
            "service": "services",
        }
        item_type_enum = item_type_mapping.get(item_type)
        if item_type_enum:
            await list_items(call.message, item_type_enum, section=section_mapping[item_type], call=call, page=page)
            await call.answer()
            return
    if action == "purchased":
        # Вернуться в список купленных
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
            if not user:
                await call.answer("Пользователь не найден", show_alert=True)
                return
            purchases = (await db.execute(select(Purchase).where(Purchase.user_id == user.id))).scalars().all()
            if not purchases:
                await call.answer("У вас нет купленных проектов.", show_alert=True)
                return
            item_ids = [p.item_id for p in purchases if p.item_id is not None]
            items = (await db.execute(select(Item).where(Item.id.in_(item_ids)))).scalars().all()
            kb = []
            for item in items:
                kb.append([InlineKeyboardButton(text=item.title, callback_data=f"item:{item.id}:{item.item_type.value}")])
            kb.append([InlineKeyboardButton(text=load_texts()["buttons"]["back"], callback_data="back:main")])
            title = load_texts()["main_menu"].get("purchased_title", "Ваши купленные проекты:")
            image_path = load_texts()["main_menu"].get("images", {}).get("purchased")
            try:
                if call.message.photo:
                    if image_path and Path(image_path).is_file():
                        photo = FSInputFile(image_path)
                        await call.message.edit_media(media=InputMediaPhoto(media=photo, caption=title), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
                    else:
                        await call.message.edit_caption(caption=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
                else:
                    if image_path and Path(image_path).is_file():
                        photo = FSInputFile(image_path)
                        await call.message.answer_photo(photo=photo, caption=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
                        await call.message.delete()
                    else:
                        await call.message.edit_text(text=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            except Exception:
                await call.message.answer(text=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
                with contextlib.suppress(Exception):
                    await call.message.delete()
            await call.answer()
            return
    
    # Default: return to main menu
    try:
        if "image" in texts["main_menu"]:
            photo = FSInputFile(texts["main_menu"]["image"])
            await call.message.edit_media(
                media=InputMediaPhoto(
                    media=photo,
                    caption=texts["main_menu"]["title"],
                    parse_mode="Markdown"
                ),
                reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username))
            )
        else:
            await call.message.edit_text(texts["main_menu"]["title"], parse_mode="Markdown", reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username)))
    except FileNotFoundError:
        await call.message.edit_text(texts["main_menu"]["title"], parse_mode="Markdown", reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username)))
        try:
            if "image" in texts["main_menu"]:
                photo = FSInputFile(texts["main_menu"]["image"])
                await call.message.answer_photo(
                    photo=photo,
                    caption=texts["main_menu"]["title"],
                    parse_mode="Markdown",
                    reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username))
                )
                await call.message.delete()
            else:
                await call.message.edit_text(texts["main_menu"]["title"], parse_mode="Markdown", reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username)))
        except FileNotFoundError:
            await call.message.edit_text(texts["main_menu"]["title"], parse_mode="Markdown", reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username)))
    
    await call.answer()


@router.callback_query(F.data == "admin:create_invoice")
async def admin_create_invoice_start(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin_user(call.from_user.id, call.from_user.username):
        await call.answer("Недоступно", show_alert=True)
        return
    prompt = load_texts().get("admin", {}).get("prompts", {}).get("description", "Введите описание платежа:")
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=prompt, reply_markup=back_kb("menu:admin"))
        else:
            await call.message.edit_text(text=prompt, reply_markup=back_kb("menu:admin"))
    except Exception:
        await call.message.answer(prompt, reply_markup=back_kb("menu:admin"))
        with contextlib.suppress(Exception):
            await call.message.delete()
    await state.set_state(AdminInvoiceStates.waiting_for_description)
    await call.answer()


@router.message(AdminInvoiceStates.waiting_for_description)
async def admin_invoice_capture_description(message: Message, state: FSMContext) -> None:
    if not _is_admin_user(message.from_user.id, message.from_user.username):
        await state.clear()
        return
    desc = (message.text or "").strip()
    await state.update_data(invoice_desc=desc)
    prompt = load_texts().get("admin", {}).get("prompts", {}).get("amount", "Введите сумму в рублях:")
    await message.answer(prompt, reply_markup=back_kb("menu:admin"))
    await state.set_state(AdminInvoiceStates.waiting_for_amount)


@router.message(AdminInvoiceStates.waiting_for_amount)
async def admin_invoice_capture_amount(message: Message, state: FSMContext) -> None:
    if not _is_admin_user(message.from_user.id, message.from_user.username):
        await state.clear()
        return
    text_val = (message.text or "").strip().replace(" ", "")
    if not text_val.isdigit() or int(text_val) <= 0:
        await message.answer("Некорректная сумма. Введите целое число больше 0.", reply_markup=back_kb("menu:admin"))
        return
    amount_minor = int(text_val) * 100
    data = await state.get_data()
    description = data.get("invoice_desc") or "Счёт от администратора"
    # Создаем платёж через ЮKassa
    client = YooKassaClient()
    import uuid
    idem = str(uuid.uuid4())
    payment_id = f"admin:{message.from_user.id}:{idem}"
    try:
        resp = await client.create_payment(
            amount_minor=amount_minor,
            description=description,
            payment_id=payment_id,
            payment_method_type=None,
            metadata={"admin_invoice": True, "admin_tg_id": message.from_user.id},
            customer_email=None,
            idempotence_key=idem,
        )
        url = (resp or {}).get("confirmation", {}).get("confirmation_url")
        if not url:
            await message.answer("Не удалось получить ссылку на оплату. Попробуйте позже.")
        else:
            title = load_texts().get("admin", {}).get("result", {}).get("link_title", "Ссылка на оплату:")
            await message.answer(f"{title}\n{url}", reply_markup=payment_link_kb(url))
    except Exception:
        await message.answer("Ошибка при создании счёта. Попробуйте позже.")
    finally:
        await client.close()
    await state.clear()


@router.callback_query(F.data.startswith("item:"))
async def show_item(call: CallbackQuery) -> None:
    parts = call.data.split(":")
    item_id = parts[1]
    item_type = parts[2] if len(parts) > 2 else None
    page_from = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
    logger.info("Карточка товара: callback получен, item_id=%s, type=%s", item_id, item_type)
    async with AsyncSessionLocal() as db:
        item = (await db.execute(select(Item).where(Item.id == int(item_id)))).scalar_one_or_none()
        # Проверим, куплен ли уже товар пользователем
        purchased = False
        try:
            user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
            if user:
                purchased = (await db.execute(
                    select(Purchase).where(Purchase.user_id == user.id, Purchase.item_id == int(item_id))
                )).first() is not None
        except Exception:
            purchased = False
        if not item:
            logger.error(f"Товар не найден: id={item_id}")
            await call.answer(f"Товар не найден: id={item_id}", show_alert=True)
            return
        caption = (
            f"*{item.title}*\n\n"
            f"{item.description}\n\n"
            f"💰 Цена: `{item.price_minor/100:.2f}` ₽"
        )
        logger.info("Показываем карточку: %s (id=%s, type=%s)", item.title, item.id, item.item_type)
        try:
            # Определяем тип исходного сообщения
            if call.message.photo:
                # Было фото — попробуем заменить картинку корректным источником или дефолтом
                media_source = None
                if item.image_file_id:
                    if item.image_file_id.startswith("http") or item.image_file_id.startswith("AgAC"):
                        media_source = item.image_file_id
                    elif Path(item.image_file_id).is_file():
                        media_source = FSInputFile(item.image_file_id)

                if not media_source:
                    # Фолбэк: дефолтные изображения по типу товара
                    texts = load_texts()
                    defaults = texts.get("defaults", {}).get("images", {})
                    key = {
                        ItemType.SERVICE: "service",
                        ItemType.DIGITAL: "digital",
                    }.get(item.item_type)
                    default_path = defaults.get(key) if key else None
                    if default_path and Path(default_path).is_file():
                        media_source = FSInputFile(default_path)

                if media_source:
                    await call.message.edit_media(
                        media=InputMediaPhoto(
                            media=media_source,
                            caption=caption,
                            parse_mode="Markdown"
                        ),
                        reply_markup=item_card_kb(item.id, item_type, purchased, from_purchased=(call.message.caption and "Ваши купленные проекты:" in call.message.caption), page=page_from)
                    )
                    logger.info("Карточка показана (edit_media), id=%s", item.id)
                else:
                    # Если не удалось определить изображение — обновим только подпись
                    await call.message.edit_caption(
                        caption=caption,
                        parse_mode="Markdown",
                        reply_markup=item_card_kb(item.id, item_type, purchased, from_purchased=(call.message.caption and "Ваши купленные проекты:" in call.message.caption), page=page_from)
                    )
                    logger.info("Карточка показана (edit_caption без изображения), id=%s", item.id)
            else:
                # Был текст — используем edit_text
                await call.message.edit_text(
                    text=caption,
                    parse_mode="Markdown",
                    reply_markup=item_card_kb(item.id, item_type, purchased, from_purchased=False, page=page_from)
                )
                logger.info("Карточка показана (edit_text), id=%s", item.id)
        except Exception as e:
            logger.error(f"Ошибка при показе карточки товара: {e}")
            await call.answer("Ошибка при показе карточки товара", show_alert=True)
        await call.answer()


async def list_items(message: Message, item_type: ItemType, section: str = None, call: CallbackQuery = None, page: int = 1, page_size: int = 5) -> None:
    texts = load_texts()
    from aiogram.exceptions import TelegramBadRequest
    async with AsyncSessionLocal() as db:
        base_stmt = select(Item).where(Item.item_type == item_type, Item.is_visible == True)
        total = (await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one()
        items = (await db.execute(
            base_stmt.order_by(Item.id.desc()).offset((page-1)*page_size).limit(page_size)
        )).scalars().all()
        purchased_ids: set[int] = set()
        try:
            # Получим список купленных пользователем товаров по users.id
            tg = message.chat.id if message else (call.from_user.id if call else None)
            if tg:
                user = (await db.execute(select(User).where(User.tg_id == tg))).scalar_one_or_none()
                if user:
                    purchases = (await db.execute(
                        select(Purchase.item_id).where(Purchase.user_id == user.id)
                    )).scalars().all()
                    purchased_ids = set(int(x) for x in purchases if x)
        except Exception:
            purchased_ids = set()
    if not items:
        empty_key = {
            ItemType.DIGITAL: "items",
            ItemType.SERVICE: "service",
        }.get(item_type, "items")
        empty_text = texts.get("empty", {}).get(empty_key, "Товаров пока-что нет, но вы держитесь!")
        if call:
            await call.answer(empty_text, show_alert=True)
            return
        else:
            await message.answer(empty_text, reply_markup=back_kb("back:main"))
            return
    if section is None:
        section_mapping = {
            ItemType.DIGITAL: "projects",
            ItemType.SERVICE: "services",
        }
        section = section_mapping.get(item_type)
    description = texts["main_menu"]["section_descriptions"].get(section, "Список")
    image_path = texts["main_menu"].get("images", {}).get(section)
    try:
        if call:
            if image_path:
                photo = FSInputFile(image_path)
                try:
                    await call.message.edit_media(
                        media=InputMediaPhoto(
                            media=photo,
                            caption=description,
                        ),
                        reply_markup=items_list_kb(items, item_type.value, purchased_ids, page=page, total=total, page_size=page_size)
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" in str(e):
                        pass
                    else:
                        raise
            else:
                try:
                    await call.message.edit_text(
                        text=description,
                        reply_markup=items_list_kb(items, item_type.value, purchased_ids, page=page, total=total, page_size=page_size)
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" in str(e):
                        pass
                    else:
                        raise
        else:
            if image_path:
                photo = FSInputFile(image_path)
                await message.answer_photo(
                    photo=photo,
                    caption=description,
                    reply_markup=items_list_kb(items, item_type.value, purchased_ids, page=page, total=total, page_size=page_size)
                )
            else:
                await message.answer(
                    text=description,
                    reply_markup=items_list_kb(items, item_type.value, purchased_ids, page=page, total=total, page_size=page_size)
                )
    except FileNotFoundError:
        if call:
            try:
                await call.message.edit_text(description, reply_markup=items_list_kb(items, item_type.value, page=page, total=total, page_size=page_size))
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    raise
        else:
            await message.answer(description, reply_markup=items_list_kb(items, item_type.value, page=page, total=total, page_size=page_size))


@router.message(StateFilter(None))
async def fallback_message(message: Message) -> None:
    texts = load_texts()
    text = texts.get("fallback", {}).get("text") or "Я пока не умею отвечать на такие сообщения."
    await message.answer(text, reply_markup=main_menu_only_kb())


@router.callback_query(F.data.startswith("donate:set:"))
async def donate_set_amount(call: CallbackQuery) -> None:
    _, _, amount = call.data.split(":")
    amount_int = int(amount)
    # Создаём донат сразу и показываем кнопку оплаты
    async with OrdersClient() as client:
        try:
            url = await client.create_order(None, call.from_user.id, amount_minor=amount_int * 100)
            try:
                texts = load_texts()
                thanks = texts.get("donate", {}).get("thanks", "Спасибо за поддержку!")
                if call.message.photo:
                    await call.message.edit_caption(caption=thanks, reply_markup=payment_link_kb(url))
                else:
                    await call.message.edit_text(text=thanks, reply_markup=payment_link_kb(url))
            except Exception:
                try:
                    thanks = load_texts().get("donate", {}).get("thanks", "Спасибо за поддержку!")
                    if call.message.photo:
                        await call.message.edit_caption(caption=thanks, reply_markup=payment_link_kb(url))
                    else:
                        await call.message.edit_text(text=thanks, reply_markup=payment_link_kb(url))
                except Exception:
                    await call.message.answer("Ссылка на оплату:", reply_markup=payment_link_kb(url))
        except Exception:
            await call.message.answer("Не удалось создать донат. Попробуйте позже.")
    await call.answer()


@router.callback_query(F.data == "donate:custom")
async def donate_custom_prompt(call: CallbackQuery, state: FSMContext) -> None:
    donate_image = load_texts().get("donate", {}).get("image")
    image_exists = bool(donate_image and Path(donate_image).is_file())
    try:
        if call.message.photo:
            if image_exists:
                photo = FSInputFile(donate_image)
                await call.message.edit_media(
                    media=InputMediaPhoto(media=photo, caption="Введите сумму в рублях:"),
                    reply_markup=back_kb("menu:donate")
                )
            else:
                await call.message.edit_caption(caption="Введите сумму в рублях:", reply_markup=back_kb("menu:donate"))
        else:
            if image_exists:
                photo = FSInputFile(donate_image)
                await call.message.answer_photo(photo=photo, caption="Введите сумму в рублях:", reply_markup=back_kb("menu:donate"))
                await call.message.delete()
            else:
                await call.message.edit_text("Введите сумму в рублях:", reply_markup=back_kb("menu:donate"))
    except Exception:
        await call.message.answer("Введите сумму в рублях:", reply_markup=back_kb("menu:donate"))
        with contextlib.suppress(Exception):
            await call.message.delete()
    await state.set_state(DonateStates.waiting_for_amount)
    await call.answer()





@router.callback_query(F.data == "donate:custom")
async def donate_custom_prompt(call: CallbackQuery, state: FSMContext) -> None:
    donate_image = load_texts().get("donate", {}).get("image")
    image_exists = bool(donate_image and Path(donate_image).is_file())
    try:
        if call.message.photo:
            if image_exists:
                photo = FSInputFile(donate_image)
                await call.message.edit_media(
                    media=InputMediaPhoto(media=photo, caption="Введите сумму в рублях:"),
                    reply_markup=back_kb("menu:donate")
                )
            else:
                await call.message.edit_caption(caption="Введите сумму в рублях:", reply_markup=back_kb("menu:donate"))
        else:
            if image_exists:
                photo = FSInputFile(donate_image)
                await call.message.answer_photo(photo=photo, caption="Введите сумму в рублях:", reply_markup=back_kb("menu:donate"))
                await call.message.delete()
            else:
                await call.message.edit_text("Введите сумму в рублях:", reply_markup=back_kb("menu:donate"))
    except Exception:
        await call.message.answer("Введите сумму в рублях:", reply_markup=back_kb("menu:donate"))
        with contextlib.suppress(Exception):
            await call.message.delete()
    await state.set_state(DonateStates.waiting_for_amount)
    await call.answer()


@router.message(DonateStates.waiting_for_amount)
async def donate_custom_amount(message: Message, state: FSMContext) -> None:
    text_val = (message.text or "").strip()
    if not text_val.isdigit() or int(text_val) <= 0:
        await message.answer("Некорректная сумма. Введите целое число больше 0.", reply_markup=back_kb("menu:donate"))
        return
    amount = int(text_val)
    # Создаём донат и сразу отдаём кнопку оплаты
    async with OrdersClient() as client:
        try:
            url = await client.create_order(None, message.from_user.id, amount_minor=amount * 100)
            thanks = load_texts().get("donate", {}).get("thanks", "Спасибо за поддержку!")
            await message.answer(thanks, reply_markup=payment_link_kb(url))
        except Exception:
            await message.answer("Не удалось создать донат. Попробуйте позже.")
    await state.clear()