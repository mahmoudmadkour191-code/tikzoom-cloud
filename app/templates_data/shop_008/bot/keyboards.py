from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.utils.texts import load_texts
from app.config import settings

def main_menu_kb(texts: dict, is_admin: bool = False) -> InlineKeyboardMarkup:
    b = texts["main_menu"]["buttons"]
    row1 = [
        InlineKeyboardButton(text=b["projects"], callback_data="menu:projects"),
    ]
    row2 = [InlineKeyboardButton(text=b["services"], callback_data="menu:services")]
    row3 = [InlineKeyboardButton(text=b["purchased"], callback_data="menu:purchased")]
    row4 = []
    if settings.show_donate_button:
        row4 = [InlineKeyboardButton(text=b["donate"], callback_data="menu:donate")]
    if settings.show_contact_button and settings.admin_tg_username:
        row5 = [InlineKeyboardButton(text=b["contact"], url=f"https://t.me/{settings.admin_tg_username.lstrip('@')}")]
    elif settings.show_contact_button:
        row5 = [InlineKeyboardButton(text=b["contact"], callback_data="menu:contact")]
    rows = [row1, row2, row3]
    if row4:
        rows.append(row4)
    if is_admin:
        rows.append([InlineKeyboardButton(text=b.get("admin", "🛠 Администрирование"), callback_data="menu:admin")])
    if settings.show_contact_button:
        rows.append(row5)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_kb(cb_data: str = "back:main") -> InlineKeyboardMarkup:
    texts = load_texts()
    kb = [[InlineKeyboardButton(text=texts["buttons"]["back"], callback_data=cb_data)]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def items_list_kb(items: list, item_type: str, purchased_ids: set[int] | None = None, page: int = 1, total: int | None = None, page_size: int = 5) -> InlineKeyboardMarkup:
    texts = load_texts()
    purchased_ids = purchased_ids or set()
    # Create buttons for each item
    kb = []
    for item in items:
        title = item.title
        if item_type == "digital" and item.id in purchased_ids:
            title = f"{title} (✅ Уже куплено)"
        kb.append([InlineKeyboardButton(text=title, callback_data=f"item:{item.id}:{item_type}:{page}")])
    # Add back button
    # Pagination controls + Back in one row
    controls = [InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="back:main")]
    if total is not None:
        if page > 1:
            controls.append(InlineKeyboardButton(text="◀️", callback_data=f"list:{item_type}:{page-1}"))
        if page * page_size < total:
            controls.append(InlineKeyboardButton(text="▶️", callback_data=f"list:{item_type}:{page+1}"))
    if controls:
        kb.append(controls)
    return InlineKeyboardMarkup(inline_keyboard=kb)

def item_card_kb(item_id: int, item_type: str, purchased: bool = False, from_purchased: bool = False, page: int = 1) -> InlineKeyboardMarkup:
    texts = load_texts()
    rows = []
    back_cb = "back:purchased" if from_purchased else f"back:list:{item_type}:{page}"
    if not purchased or item_type == "service":
        rows.append([InlineKeyboardButton(text=texts["buttons"].get("buy", "Купить"), callback_data=f"buy_one:{item_id}")])
    else:
        rows.append([InlineKeyboardButton(text="✅ Уже куплено", callback_data=back_cb)])
    rows.append([InlineKeyboardButton(text=texts["buttons"]["back"], callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def payment_method_kb(item_id: int) -> InlineKeyboardMarkup:
    texts = load_texts()
    kb = [
        [InlineKeyboardButton(text=texts["buttons"].get("buy", "Купить"), callback_data=f"buy_one:{item_id}")],
        [InlineKeyboardButton(text=texts["buttons"]["back"], callback_data=f"back:item:{item_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def main_menu_only_kb() -> InlineKeyboardMarkup:
    texts = load_texts()
    kb = [[InlineKeyboardButton(text=texts["buttons"]["main_menu"], callback_data="back:main")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def payment_link_kb(url: str) -> InlineKeyboardMarkup:
    texts = load_texts()
    kb = [
        [InlineKeyboardButton(text=texts["payment"]["buttons"]["pay"], url=url)],
        [InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="back:main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def admin_menu_kb() -> InlineKeyboardMarkup:
    texts = load_texts()
    b = texts.get("admin", {}).get("buttons", {})
    kb = [
        [InlineKeyboardButton(text=b.get("create_invoice", "🧾 Создать счёт"), callback_data="admin:create_invoice")],
        [InlineKeyboardButton(text=load_texts()["buttons"]["back"], callback_data="back:main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def donate_amounts_kb() -> InlineKeyboardMarkup:
    # Читаем суммы из env: формат "100,200,500"
    raw = settings.donate_amounts or "100,200,500"
    amounts = []
    try:
        amounts = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
    except Exception:
        amounts = [100, 200, 500]
    rows = []
    row = []
    for i, val in enumerate(amounts):
        row.append(InlineKeyboardButton(text=f"{val} ₽", callback_data=f"donate:set:{val}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="Ввести сумму", callback_data="donate:custom")])
    rows.append([InlineKeyboardButton(text=load_texts()["buttons"]["back"], callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
