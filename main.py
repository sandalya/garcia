import os
import asyncio
from datetime import time
from zoneinfo import ZoneInfo
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
from modules.digest import DigestModule
from modules.onboarding import OnboardingModule
from modules.analyze import AnalyzeModule
from modules.curriculum import cmd_curriculum, cmd_done, handle_curriculum_callback
from modules.podcast import cmd_podcast
from modules.notebooklm import cmd_notebooks
from modules.catchup import CatchupModule

import tempfile
import base64
import anthropic
import tempfile
import base64
import anthropic
import sys as _sys
_sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace"))
from shared.logger import setup_logging
setup_logging(agent="garcia")
logger = logging.getLogger("garcia")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OWNER_CHAT_ID = int(os.environ["OWNER_CHAT_ID"])
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x]

digest = DigestModule(owner_chat_id=OWNER_CHAT_ID)
DIGEST_RECIPIENT_ID = 255525  # тільки Ксюша
digest_recipients = [DigestModule(owner_chat_id=DIGEST_RECIPIENT_ID)]
onboarding = OnboardingModule(owner_chat_id=OWNER_CHAT_ID)
analyze = AnalyzeModule(owner_chat_id=OWNER_CHAT_ID)
catchup = CatchupModule(owner_chat_id=OWNER_CHAT_ID)

CATCHUP_PERIODS = {"3d": 3, "7d": 7, "14d": 14, "30d": 30, "60d": 60, "180d": 180, "365d": 365}


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привіт, я Гарсіа — твій асистент з packaging design!\n\n"
        "Що вмію:\n"
        "🔍 /analyze — аналіз твого Pinterest-борду\n"
        "📚 /onboarding — що таке packaging artist і як починати\n"
        "🗺 /cur — навчальний план\n"
        "✅ /done <N> — позначити тему виконаною\n"
        "🎧 /podcast [N] [deep] — аудіо-епізод по темі\n"
        "📓 /notebooks — мої NotebookLM notebooks\n"
        "📰 /digest — дайджест новин packaging design\n"
        "🗓 /catchup [7d|30d|...] — ретроспектива новин\n\n"
        "Або просто пиши — відповім!"
    )


async def cmd_catchup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    arg = (context.args[0] if context.args else "7d").lower()
    days = CATCHUP_PERIODS.get(arg, 7)
    await catchup.send_catchup(update, days)


PROFILE_KEYWORDS = ["профайл", "профіл", "profile", "фрілансер", "freelancer", "upwork", "behance", "dribbble"]


def _is_profile_request(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in PROFILE_KEYWORDS)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS and update.effective_user.id != OWNER_CHAT_ID:
        return
    await update.message.chat.send_action("typing")
    text = update.message.text
    if _is_profile_request(text):
        response = digest.call_claude_profiles(text)
    else:
        response = digest.call_claude_chat(text, max_tokens=1500)
    await update.message.reply_text(response or "Не змогла відповісти, спробуй ще раз.")


async def _download_photo(update, context, user_id: int):
    from pathlib import Path
    import os, tempfile
    msg = update.message
    if msg.photo:
        suffix = ".jpg"
        file_id = msg.photo[-1].file_id
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("image/"):
        suffix = Path(msg.document.file_name).suffix if msg.document.file_name else ".jpg"
        file_id = msg.document.file_id
    else:
        return None
    import os, tempfile
    file = await context.bot.get_file(file_id)
    import time as _t
    tmp_path = os.path.join(tempfile.gettempdir(), f"garcia_photo_{user_id}_{int(_t.time()*1000)}{suffix}")
    await file.download_to_drive(tmp_path)
    return tmp_path


import asyncio as _asyncio
_mg_buffers: dict = {}

async def _vision_reply(paths: list, caption: str, system: str) -> str:
    import base64, anthropic, os
    from pathlib import Path
    MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp",
            ".heic": "image/jpeg", ".heif": "image/jpeg"}
    ai = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    content = []
    if caption:
        content.append({"type": "text", "text": caption})
    for img_path in paths:
        try:
            raw = Path(img_path).read_bytes()
            suffix = Path(img_path).suffix.lower()
            mime = MIME.get(suffix, "image/jpeg")
            b64 = base64.standard_b64encode(raw).decode()
            content.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}})
        except Exception as e:
            logger.warning(f"_vision_reply skip {img_path}: {e}")
    if not content:
        return ""
    resp = ai.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": content}],
    )
    return resp.content[0].text if resp.content else ""

async def _flush_mg(media_group_id: str):
    await _asyncio.sleep(1.5)
    buf = _mg_buffers.pop(media_group_id, None)
    if not buf:
        return
    update = buf["update"]
    await update.message.chat.send_action("typing")
    system = digest._build_system(include_memory=True, include_conversation=False)
    resp = await _vision_reply(buf["paths"], buf["caption"], system)
    await update.message.reply_text(resp or "Не змогла відповісти, спробуй ще раз.")

async def _add_to_mg(mg_id: str, path: str, caption: str, uid: int, update):
    if mg_id in _mg_buffers:
        _mg_buffers[mg_id]["paths"].append(path)
        if caption and not _mg_buffers[mg_id]["caption"]:
            _mg_buffers[mg_id]["caption"] = caption
        _mg_buffers[mg_id]["task"].cancel()
    else:
        _mg_buffers[mg_id] = {"paths": [path], "caption": caption, "uid": uid, "update": update, "task": None}
    task = _asyncio.get_event_loop().create_task(_flush_mg(mg_id))
    _mg_buffers[mg_id]["task"] = task

async def handle_photo(update, context):
    if update.effective_user.id not in ADMIN_IDS and update.effective_user.id != OWNER_CHAT_ID:
        return
    uid = update.effective_user.id
    path = await _download_photo(update, context, uid)
    if not path:
        return
    caption = (update.message.caption or "").strip()
    mg_id = update.message.media_group_id
    if mg_id:
        await _add_to_mg(mg_id, path, caption, uid, update)
    else:
        await update.message.chat.send_action("typing")
        system = digest._build_system(include_memory=True, include_conversation=False)
        resp = await _vision_reply([path], caption, system)
        await update.message.reply_text(resp or "Не змогла відповісти, спробуй ще раз.")

async def handle_document(update, context):
    if update.effective_user.id not in ADMIN_IDS and update.effective_user.id != OWNER_CHAT_ID:
        return
    doc = update.message.document
    if not (doc and doc.mime_type and doc.mime_type.startswith("image/")):
        return
    uid = update.effective_user.id
    path = await _download_photo(update, context, uid)
    if not path:
        return
    caption = (update.message.caption or "").strip()
    mg_id = update.message.media_group_id
    if mg_id:
        await _add_to_mg(mg_id, path, caption, uid, update)
    else:
        await update.message.chat.send_action("typing")
        system = digest._build_system(include_memory=True, include_conversation=False)
        resp = await _vision_reply([path], caption, system)
        await update.message.reply_text(resp or "Не змогла відповісти, спробуй ще раз.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("analyze", analyze.cmd_analyze))
    app.add_handler(CommandHandler("onboarding", lambda u, c: onboarding.send_menu(u)))
    app.add_handler(CommandHandler("digest", lambda u, c: digest.send(u)))
    app.add_handler(CommandHandler("cur", cmd_curriculum))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("podcast", cmd_podcast))
    app.add_handler(CommandHandler("notebooks", cmd_notebooks))
    app.add_handler(CommandHandler("catchup", cmd_catchup))
    app.add_handler(CallbackQueryHandler(handle_curriculum_callback, pattern="^cur_"))
    app.add_handler(CallbackQueryHandler(onboarding.handle_callback, pattern="^onb_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Garcia started")

    async def daily_digest(ctx):
        for d in digest_recipients:
            await d.send(ctx.application)

    app.job_queue.run_daily(
        daily_digest,
        time=time(hour=9, minute=0, tzinfo=ZoneInfo("Europe/Kiev"))
    )

    app.run_polling()


if __name__ == "__main__":
    main()
