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

import sys as _sys
_sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace"))
from shared.logger import setup_logging
setup_logging(agent="garcia")
logger = logging.getLogger("garcia")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OWNER_CHAT_ID = int(os.environ["OWNER_CHAT_ID"])
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x]

digest = DigestModule(owner_chat_id=OWNER_CHAT_ID)
digest_recipients = [DigestModule(owner_chat_id=uid) for uid in ADMIN_IDS]
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


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS and update.effective_user.id != OWNER_CHAT_ID:
        return
    from modules.base import BaseModule
    base = BaseModule(owner_chat_id=OWNER_CHAT_ID)
    response = base.call_claude(update.message.text, max_tokens=1024, smart=True)
    await update.message.reply_text(response)


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
