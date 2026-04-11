"""
Модуль curriculum — персональний план навчання Packaging Design.
Команди: /cur, /done <N>
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .base import DATA_DIR

log = logging.getLogger("garcia.curriculum")

CURRICULUM_STATE_PATH = DATA_DIR / "curriculum.json"

CURRICULUM = [
    {
        "id": 1,
        "title": "Основи dieline і розгортки",
        "estimate": "2-3 дні",
        "why": "Без розуміння розгортки неможливо зробити упаковку — це фундамент всього.",
        "read": "https://www.thepackagingcompany.com/knowledge-center/dieline-design-guide",
        "do": "Скачати безкоштовний dieline коробки з lovelypackage.com і обвести в Illustrator.",
    },
    {
        "id": 2,
        "title": "Типографіка для упаковки",
        "estimate": "2-3 дні",
        "why": "Шрифт на упаковці — це не просто текст, це частина бренду і UX покупця.",
        "read": "https://www.packaging-gateway.com/features/typography-packaging-design/",
        "do": "Взяти один зі своїх botanical референсів і розібрати які шрифти використані і чому.",
    },
    {
        "id": 3,
        "title": "Колір і кольорові моделі (CMYK vs RGB)",
        "estimate": "1-2 дні",
        "why": "Колір на екрані і в друці — різні речі. Помилка коштує грошей клієнту.",
        "read": "https://www.printingforless.com/cmyk-vs-rgb.html",
        "do": "Взяти свою улюблену палітру з Pinterest і конвертувати в CMYK. Порівняти різницю.",
    },
    {
        "id": 4,
        "title": "Матеріали і технології друку",
        "estimate": "3-4 дні",
        "why": "Знання матеріалів відрізняє дизайнера від упакувальника. Клієнти платять за це.",
        "read": "https://www.designpackaging.com/packaging-materials-guide",
        "do": "Знайти 5 прикладів botanical packaging і визначити які матеріали і техніки друку використано (фольга, тиснення, крафт тощо).",
    },
    {
        "id": 5,
        "title": "Перше портфоліо: 3 концепти",
        "estimate": "1-2 тижні",
        "why": "Без портфоліо немає клієнтів. 3 strong концепти краще ніж 10 слабких.",
        "read": "https://www.behance.net/search/projects/packaging",
        "do": "Зробити 3 концепти упаковки в своєму стилі (botanical/floral). Можна для вигаданих брендів. Викласти на Behance.",
    },
    {
        "id": 6,
        "title": "Мокапи і презентація роботи",
        "estimate": "2-3 дні",
        "why": "Навіть гарний дизайн виглядає слабко без якісного мокапу. Це продає.",
        "read": "https://www.mockupworld.co/all-mockups/packaging/",
        "do": "Взяти один зі своїх концептів і зробити 3 мокапи в різних середовищах (на столі, в руках, flatlay).",
    },
    {
        "id": 7,
        "title": "Перший клієнт і ціноутворення",
        "estimate": "ongoing",
        "why": "Перший реальний проект дає більше досвіду ніж 10 концептів.",
        "read": "https://www.creativeboom.com/tips/how-to-price-your-packaging-design/",
        "do": "Розмістити оголошення на Behance або Upwork. Перший проект можна зробити за символічну ціну для відгуку.",
    },
]


def load_state() -> dict:
    if CURRICULUM_STATE_PATH.exists():
        return json.loads(CURRICULUM_STATE_PATH.read_text())
    return {"completed": [], "started": [], "notes": {}}


def save_state(state: dict):
    CURRICULUM_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def _status_icon(item_id: int, state: dict) -> str:
    if item_id in state["completed"]:
        return "✅"
    if item_id in state["started"]:
        return "🔄"
    return "⬜"


def _progress_bar(state: dict) -> str:
    total = len(CURRICULUM)
    done = len(state["completed"])
    filled = round(done / total * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"[{bar}] {done}/{total}"


async def cmd_curriculum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    lines = [f"🗺 Твій Packaging Design Curriculum\n{_progress_bar(state)}\n"]

    for item in CURRICULUM:
        icon = _status_icon(item["id"], state)
        lines.append(f"{icon} {item['id']}. {item['title']} — {item['estimate']}")

    lines.append("\n/done N — виконано")

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            f"{_status_icon(item['id'], state)} {item['id']}",
            callback_data=f"cur_item|{item['id']}"
        )
        for item in CURRICULUM
    ]])

    await update.message.reply_text("\n".join(lines), reply_markup=keyboard)


async def cmd_curriculum_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Використання: /cur")
        return
    item_id = int(args[0])
    item = next((i for i in CURRICULUM if i["id"] == item_id), None)
    if not item:
        await update.message.reply_text(f"Тема {item_id} не існує.")
        return
    state = load_state()
    icon = _status_icon(item_id, state)
    text = (
        f"{icon} *{item['id']}. {item['title']}*\n"
        f"⏱ {item['estimate']}\n\n"
        f"*Навіщо:* {item['why']}\n\n"
        f"*Почитати:* [посилання]({item['read']})\n\n"
        f"*Зробити руками:*\n{item['do']}"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Почала", callback_data=f"cur_start|{item_id}"),
        InlineKeyboardButton("✅ Готово", callback_data=f"cur_done|{item_id}"),
    ]])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Використання: /done <N>")
        return
    await _mark(update, int(args[0]), "done")


async def cmd_start_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Використання: /begin <N>")
        return
    await _mark(update, int(args[0]), "start")


async def _mark(update: Update, item_id: int, action: str):
    item = next((i for i in CURRICULUM if i["id"] == item_id), None)
    if not item:
        await update.message.reply_text(f"Тема {item_id} не існує.")
        return
    state = load_state()
    if action == "done":
        if item_id not in state["completed"]:
            state["completed"].append(item_id)
        if item_id in state["started"]:
            state["started"].remove(item_id)
        state["notes"][str(item_id)] = {"completed_at": datetime.now().isoformat()}
        save_state(state)
        next_item = next((i for i in CURRICULUM if i["id"] not in state["completed"]), None)
        msg = f"✅ *{item['title']}* — виконано!\n\n{_progress_bar(state)}"
        if next_item:
            msg += f"\n\nНаступна тема: *{next_item['id']}. {next_item['title']}*"
        else:
            msg += "\n\n🎉 Curriculum завершено! Ти тепер справжній packaging designer!"
        await update.message.reply_text(msg, parse_mode="Markdown")
    elif action == "start":
        if item_id not in state["started"] and item_id not in state["completed"]:
            state["started"].append(item_id)
        save_state(state)
        await update.message.reply_text(
            f"🔄 *{item['title']}* — в процесі. Удачі!",
            parse_mode="Markdown"
        )


async def handle_curriculum_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("|")
    action, item_id = parts[0], int(parts[1])
    state = load_state()
    item = next((i for i in CURRICULUM if i["id"] == item_id), None)
    if not item:
        return

    if action == "cur_item":
        icon = _status_icon(item_id, state)
        text = (
            f"{icon} *{item['id']}. {item['title']}*\n"
            f"⏱ {item['estimate']}\n\n"
            f"*Навіщо:* {item['why']}\n\n"
            f"*Почитати:* [посилання]({item['read']})\n\n"
            f"*Зробити руками:*\n{item['do']}"
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Почала", callback_data=f"cur_start|{item_id}"),
            InlineKeyboardButton("✅ Готово", callback_data=f"cur_done|{item_id}"),
        ]])
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

    elif action == "cur_done":
        if item_id not in state["completed"]:
            state["completed"].append(item_id)
        if item_id in state["started"]:
            state["started"].remove(item_id)
        state["notes"][str(item_id)] = {"completed_at": datetime.now().isoformat()}
        save_state(state)
        await query.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("✅ Виконано!", callback_data="done")]])
        )

    elif action == "cur_start":
        if item_id not in state["started"] and item_id not in state["completed"]:
            state["started"].append(item_id)
        save_state(state)
        await query.edit_message_reply_markup(
            InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 В процесі", callback_data="done"),
                InlineKeyboardButton("✅ Готово", callback_data=f"cur_done|{item_id}"),
            ]])
        )
