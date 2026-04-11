import os
import json
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from modules.base import BaseModule, DATA_DIR

ANALYSIS_PATH = DATA_DIR / "pinterest_analysis.json"

class AnalyzeModule(BaseModule):

    def _load_analysis(self) -> dict:
        if ANALYSIS_PATH.exists():
            return json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))
        return {}

    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin_ids = [self.owner_chat_id] + [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x]
        if update.effective_user.id not in admin_ids:
            return

        data = self._load_analysis()
        if not data:
            await update.message.reply_text("❌ Аналіз не знайдено. Спочатку запусти скрипт збору даних.")
            return

        lines = ["📊 *Аналіз твого Pinterest-борду Packaging*\n"]

        lines.append("🎨 *Топ-5 стилів:*")
        for s in data.get("top_styles", []):
            lines.append(f"{s['rank']}. *{s['style']}* — {s['count']} пінів\n   _{s['description']}_")

        lines.append("\n📦 *Топ-5 товарів:*")
        for p in data.get("top_products", []):
            lines.append(f"{p['rank']}. {p['product']} — {p['count']} пінів")

        lines.append("\n🎨 *Топ-5 кольорових палітр:*")
        for pal in data.get("top_palettes", []):
            colors = " ".join(pal["colors"][:3])
            lines.append(f"{pal['rank']}. *{pal['name']}* — {pal['mood']}\n   `{colors}`")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
