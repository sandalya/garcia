import os
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
onboarding = OnboardingModule(owner_chat_id=OWNER_CHAT_ID)
analyze = AnalyzeModule(owner_chat_id=OWNER_CHAT_ID)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привіт, я Гарсія — твій асистент з пакування!\n\n"
        "Що вмію:\n"
        "🔍 /analyze — аналіз твого Pinterest-борду\n"
        "📚 /onboarding — що таке packaging artist і як починати\n"
        "🗺 /curriculum — навчальний план\n"
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
    app.add_handler(CommandHandler("onboarding", onboarding.send_menu))
    app.add_handler(CommandHandler("digest", digest.send))
    app.add_handler(CommandHandler("cur", cmd_curriculum))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CallbackQueryHandler(handle_curriculum_callback, pattern="^cur:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Garcia started")
    app.run_polling()

if __name__ == "__main__":
    main()
