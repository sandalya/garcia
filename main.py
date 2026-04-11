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
)
from modules.digest import DigestModule
from modules.onboarding import OnboardingModule
from modules.analyze import AnalyzeModule
from modules.curriculum import (
    cmd_curriculum, cmd_curriculum_item, cmd_done,
    cmd_start_topic, handle_curriculum_callback,
)
from telegram.ext import CallbackQueryHandler
import sys as _sys
_sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace"))
from shared.logger import setup_logging
setup_logging(agent="garcia")
logger = logging.getLogger("garcia")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OWNER_CHAT_ID = int(os.environ["OWNER_CHAT_ID"])

digest = DigestModule(owner_chat_id=OWNER_CHAT_ID)
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x]
digest_recipients = [DigestModule(owner_chat_id=uid) for uid in ADMIN_IDS]
onboarding = OnboardingModule(owner_chat_id=OWNER_CHAT_ID)
analyze = AnalyzeModule(owner_chat_id=OWNER_CHAT_ID)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привіт, я Гарсіа — твій асистент з пакування!\n\n"
        "Що вмію:\n"
        "🔍 /analyze — аналіз твого Pinterest-борду\n"
        "📚 /onboarding — що таке packaging artist і як починати\n"
        "🗺 /cur — навчальний план\n"
        "📰 /digest — дайджест новин packaging design\n\n"
        "Або просто пиши — відповім!"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_CHAT_ID:
        return
    user_text = update.message.text
    from modules.base import BaseModule
    base = BaseModule(owner_chat_id=OWNER_CHAT_ID)
    response = base.call_claude(user_text, max_tokens=1024, smart=True)
    await update.message.reply_text(response)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("analyze", analyze.cmd_analyze))
    app.add_handler(CommandHandler("onboarding", lambda u, c: onboarding.send_menu(u)))
    app.add_handler(CommandHandler("digest", lambda u, c: digest.send(u)))
    app.add_handler(CommandHandler("cur", cmd_curriculum))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CallbackQueryHandler(handle_curriculum_callback, pattern="^cur_"))
    app.add_handler(CallbackQueryHandler(onboarding.handle_callback, pattern="^onb_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Garcia started")

    async def daily_digest(ctx):
        for d in digest_recipients:
            await d.send(ctx.application)
    app.job_queue.run_daily(daily_digest, time=time(hour=9, minute=0, tzinfo=ZoneInfo("Europe/Kiev")))

    # Щоденний дайджест о 9:00
    job_queue = app.job_queue
    job_queue.run_daily(
        lambda ctx: asyncio.ensure_future(digest.send_to(ctx, int(os.environ["ADMIN_IDS"].split(",")[0]))),
        time=time(hour=9, minute=0),
    )
    app.run_polling()

if __name__ == "__main__":
    main()
