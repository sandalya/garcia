"""
Garcia — персональний beauty-асистент Ксю.
Agentic loop: Garcia сама вирішує що робити з кожним повідомленням.
"""
import os
import asyncio
import logging
import tempfile
import base64
from pathlib import Path
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import sys as _sys
_sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace"))
from shared.logger import setup_logging
setup_logging(agent="garcia")
logger = logging.getLogger("garcia")

from modules.brain import GarciaBrain

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OWNER_CHAT_ID = int(os.environ["OWNER_CHAT_ID"])
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x]

brain = GarciaBrain()

BUFFER_WAIT = 3.5
_buffers: dict[int, dict] = {}

MIME_MAP = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".webp": "image/webp",
    ".heic": "image/jpeg", ".heif": "image/jpeg",
}


def _is_authorized(user_id: int) -> bool:
    return user_id in ADMIN_IDS or user_id == OWNER_CHAT_ID


async def _download_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str | None:
    msg = update.message
    if msg.photo:
        suffix = ".jpg"
        file_id = msg.photo[-1].file_id
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("image/"):
        suffix = Path(msg.document.file_name).suffix if msg.document.file_name else ".jpg"
        file_id = msg.document.file_id
    else:
        return None
    import time as _t
    file = await context.bot.get_file(file_id)
    tmp_path = os.path.join(tempfile.gettempdir(), f"garcia_{user_id}_{int(_t.time()*1000)}{suffix}")
    await file.download_to_drive(tmp_path)
    return tmp_path


async def _get_reply_images(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> list:
    reply = update.message.reply_to_message
    if not reply:
        return []
    paths = []
    if reply.document and reply.document.mime_type and reply.document.mime_type.startswith("image/"):
        file = await context.bot.get_file(reply.document.file_id)
        suffix = Path(reply.document.file_name).suffix if reply.document.file_name else ".png"
        import time as _t
        tmp_path = os.path.join(tempfile.gettempdir(), f"garcia_reply_{user_id}_0{suffix}")
        await file.download_to_drive(tmp_path)
        paths.append(tmp_path)
    elif reply.photo:
        file = await context.bot.get_file(reply.photo[-1].file_id)
        import time as _t
        tmp_path = os.path.join(tempfile.gettempdir(), f"garcia_reply_{user_id}_0.jpg")
        await file.download_to_drive(tmp_path)
        paths.append(tmp_path)
    return paths


def _paths_to_image_data(paths: list) -> list:
    image_data = []
    for img_path in paths:
        try:
            raw = Path(img_path).read_bytes()
            suffix = Path(img_path).suffix.lower()
            mime = MIME_MAP.get(suffix, "image/jpeg")
            b64 = base64.standard_b64encode(raw).decode()
            image_data.append({
                "type": "image",
                "source": {"type": "base64", "media_type": mime, "data": b64}
            })
        except Exception as e:
            logger.warning(f"Skip image {img_path}: {e}")
    return image_data


def _cancel_buffer(user_id: int):
    if user_id in _buffers and _buffers[user_id].get("task"):
        _buffers[user_id]["task"].cancel()


async def _flush_buffer(user_id: int):
    await asyncio.sleep(BUFFER_WAIT)
    buf = _buffers.pop(user_id, None)
    if not buf:
        return
    update = buf["update"]
    text = buf.get("text", "").strip()
    paths = buf.get("image_paths", [])
    if not text and not paths:
        return
    await update.message.chat.send_action("typing")
    image_data = _paths_to_image_data(paths) if paths else None
    if not text and image_data:
        text = "Що скажеш про це фото?"
    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(None, brain.run, text, image_data)
    except Exception as e:
        logger.error(f"Brain error: {e}")
        response = "Вибач, щось пішло не так 💛 Спробуй ще раз."
    if not response:
        response = "Хм, не змогла відповісти. Спробуй переформулювати? 🤔"
    for i in range(0, len(response), 4000):
        chunk = response[i:i+4000]
        await update.message.reply_text(chunk)


async def _add_to_buffer(user_id: int, update: Update, text: str = "", image_path: str = None):
    _cancel_buffer(user_id)
    buf = _buffers.setdefault(user_id, {})
    if text:
        buf["text"] = (buf.get("text", "") + "\\n" + text).strip()
    if image_path:
        paths = buf.get("image_paths", [])
        if image_path not in paths:
            paths.append(image_path)
        buf["image_paths"] = paths
    buf["update"] = update
    task = asyncio.create_task(_flush_buffer(user_id))
    buf["task"] = task


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💄 Привіт! Я Гарсіа — твій персональний beauty-асистент!\\n\\n"
        "Що я вмію:\\n"
        "🎨 Визначити твій колірний тип — просто скинь фото\\n"
        "💋 Підібрати макіяж під твою зовнішність\\n"
        "📝 Покрокові інструкції для будь-якого образу\\n"
        "🛍 Порекомендувати якісну косметику\\n"
        "✨ Підказати зачіски і колір волосся\\n\\n"
        "Просто пиши або кидай фото — я розберуся! 💛\\n\\n"
        "Команди:\\n"
        "/start — ця підказка\\n"
        "/reset — очистити історію розмови\\n"
        "/cost — скільки коштувала ця сесія\\n"
        "/profile — що я про тебе знаю"
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update.effective_user.id):
        return
    brain.reset_history()
    await update.message.reply_text("🔄 Історію очищено! Починаємо з чистого аркуша 💛")


async def cmd_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update.effective_user.id):
        return
    await update.message.reply_text(brain.get_cost_summary())


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update.effective_user.id):
        return
    import json
    from modules.base import PROFILE_PATH
    try:
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        ca = profile.get("color_analysis", {})
        skin = profile.get("skin", {})
        mu = profile.get("makeup", {})
        products = profile.get("products", {})
        lines = ["👤 *Профіль Ксю*\\n"]
        if ca.get("skin_tone"):
            lines.append(f"🎨 Колірний тип: {ca.get('season_type', '?')}")
            lines.append(f"   Скінтон: {ca['skin_tone']}, підтон: {ca.get('skin_undertone', '?')}")
            lines.append(f"   Очі: {ca.get('eye_color', '?')}, волосся: {ca.get('hair_color', '?')}")
        else:
            lines.append("🎨 Колірний тип: ще не визначено (скинь фото!)")
        lines.append(f"\\n💆 Шкіра: {skin.get('type', 'не визначено')}")
        if skin.get("concerns"):
            lines.append(f"   Проблеми: {', '.join(skin['concerns'])}")
        lines.append(f"\\n💄 Рівень: {mu.get('level', 'beginner')}")
        if mu.get("favorite_looks"):
            lines.append(f"   Улюблені образи: {', '.join(mu['favorite_looks'])}")
        if products.get("owned"):
            lines.append(f"\\n🛍 Косметичка: {', '.join(products['owned'][:5])}")
            if len(products['owned']) > 5:
                lines.append(f"   ...і ще {len(products['owned']) - 5}")
        await update.message.reply_text("\\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Помилка читання профілю: {e}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update.effective_user.id):
        return
    text = update.message.text
    user_id = update.effective_user.id
    reply_images = await _get_reply_images(update, context, user_id)
    for path in reply_images:
        await _add_to_buffer(user_id, update, image_path=path)
    await _add_to_buffer(user_id, update, text=text)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update.effective_user.id):
        return
    user_id = update.effective_user.id
    path = await _download_photo(update, context, user_id)
    if not path:
        return
    caption = (update.message.caption or "").strip()
    await _add_to_buffer(user_id, update, text=caption, image_path=path)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update.effective_user.id):
        return
    doc = update.message.document
    if not (doc and doc.mime_type and doc.mime_type.startswith("image/")):
        return
    user_id = update.effective_user.id
    path = await _download_photo(update, context, user_id)
    if not path:
        return
    caption = (update.message.caption or "").strip()
    await _add_to_buffer(user_id, update, text=caption, image_path=path)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("cost", cmd_cost))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Garcia beauty assistant started")
    app.run_polling()


if __name__ == "__main__":
    main()
