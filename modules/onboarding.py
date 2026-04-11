import re
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base import BaseModule

logger = logging.getLogger("garcia.onboarding")

TOPICS = {
    "what": "📦 Що таке packaging design",
    "skills": "🎨 Які навички потрібні",
    "process": "⚙️ Як працює процес",
    "tools": "🛠 Інструменти та софт",
    "career": "💼 Як увійти в професію",
}

PROMPTS = {
    "what": """Поясни що таке packaging design як професія для людини яка тільки входить в цю сферу.
Покрий: що робить packaging artist/designer, яка різниця між packaging design і графічним дизайном, які типи упаковки існують (первинна, вторинна, транспортна), чому це важлива і цікава професія, які галузі найбільше потребують packaging дизайнерів.
Стиль: надихаючо і зрозуміло, з конкретними прикладами брендів. Українська мова. Без markdown-форматування, тільки звичайний текст з емодзі.""",

    "skills": """Поясни які навички потрібні packaging дизайнеру-початківцю.
Покрий: технічні навички (dielines, розгортки, друк), дизайн-навички (типографіка, колір, композиція), розуміння матеріалів і технологій друку, комунікація з клієнтами і виробниками, що варто вивчити першим а що прийде з досвідом.
Спирайся на те що Ксюша вже цікавиться botanical/floral стилем і має смак до мінімалізму та luxury естетики.
Стиль: практично і конкретно. Українська мова. Без markdown-форматування, тільки звичайний текст з емодзі.""",

    "process": """Поясни як виглядає типовий процес роботи packaging дизайнера від бріфу до друку.
Покрий: брифінг і дослідження ринку, концепція і скетчі, робота з dieline/розгорткою, вибір матеріалів і технік друку, підготовка до друку (prepress), типові помилки початківців.
Стиль: покроково, з реальними прикладами. Українська мова. Без markdown-форматування, тільки звичайний текст з емодзі.""",

    "tools": """Поясни який софт і інструменти використовують packaging дизайнери.
Покрий: Adobe Illustrator (основний інструмент), Adobe Photoshop і InDesign, спеціалізований софт (Esko, ArtiosCAD), 3D-мокапи (Cinema 4D, Blender, онлайн-сервіси), корисні ресурси і бібліотеки dieline, де брати референси і натхнення.
Стиль: практично, з посиланнями де можливо. Українська мова. Без markdown-форматування, тільки звичайний текст з емодзі.""",

    "career": """Поясни як увійти в packaging design як нова кар'єра.
Покрий: як зібрати перше портфоліо без досвіду, де шукати перших клієнтів, які платформи для фрілансу підходять, як позиціонувати себе, типовий шлях від першого проекту до стабільного доходу, скільки реально заробляють packaging дизайнери.
Враховуй що людина вже має художній смак і цікавиться botanical/floral та luxury стилями — це її перевага.
Стиль: чесно і практично, без рожевих окулярів але з оптимізмом. Українська мова. Без markdown-форматування, тільки звичайний текст з емодзі.""",
}


class OnboardingModule(BaseModule):

    def _make_menu(self) -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton(label, callback_data=f"onb_{key}")]
            for key, label in TOPICS.items()
        ]
        return InlineKeyboardMarkup(buttons)

    async def send_menu(self, update: Update):
        await update.message.reply_text(
            "🎓 <b>Онбординг: Packaging Design</b>\n\nОбери тему — розповім що треба знати:",
            parse_mode="HTML",
            reply_markup=self._make_menu(),
        )

    def _cache_path(self, key: str) -> Path:
        from .base import DATA_DIR
        return DATA_DIR / f"onboarding_{key}.txt"

    def _load_cache(self, key: str):
        from datetime import datetime, timedelta
        p = self._cache_path(key)
        if not p.exists():
            return None
        age = datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)
        if age > timedelta(days=30):
            return None
        return p.read_text()

    def _save_cache(self, key: str, text: str):
        self._cache_path(key).write_text(text)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        key = query.data.replace("onb_", "")
        if key not in PROMPTS:
            return

        topic_label = TOPICS[key]
        await query.edit_message_text(f"⏳ Готую огляд: {topic_label}...")

        try:
            cached = self._load_cache(key)
            if cached:
                text = cached
            else:
                raw = self.call_claude_with_search(PROMPTS[key], max_tokens=4000)
                text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', raw)
                text = re.sub(r'#{1,3}\s*', '', text)
                text = re.sub(r'`([^`]+)`', r'\1', text)
                self._save_cache(key, text)

            if not text:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="😶 Не вдалось отримати відповідь.")
                return

            if len(text) > 4000:
                chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for chunk in chunks:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📋 Ще тема?",
                reply_markup=self._make_menu(),
            )

        except Exception as e:
            logger.error(f"Onboarding error: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Помилка: {e}")
