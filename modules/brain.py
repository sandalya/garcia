"""
Garcia Brain — agentic reasoning loop.

Замість жорстких команд Garcia отримує повідомлення і сама вирішує
що робити: відповісти одразу, пошукати продукти, проаналізувати фото,
оновити профіль тощо.

Цикл: think → act (tools) → observe → respond
Максимум 5 кроків щоб не зʼїсти бюджет.
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional
import anthropic

from modules.base import BaseModule, GARCIA_PERSONA, PROFILE_PATH, DATA_DIR

logger = logging.getLogger("garcia")

LOG_PATH = DATA_DIR / "conversation_log.json"


def _append_log(entry: dict):
    """Додає запис в conversation_log.json."""
    import datetime
    entry["timestamp"] = datetime.datetime.now().isoformat()
    try:
        logs = []
        if LOG_PATH.exists():
            logs = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        logs.append(entry)
        # Тримаємо останні 500 записів
        if len(logs) > 500:
            logs = logs[-500:]
        LOG_PATH.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Log write error: {e}")

MAX_STEPS = 8

# --- Tools available to Garcia ---

TOOLS_SCHEMA = [
    {
        "name": "search_products",
        "description": "Пошук косметичних продуктів в інтернеті. Використовуй для рекомендацій конкретних продуктів з відгуками та цінами.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Пошуковий запит англійською для кращих результатів, напр. 'best eyeshadow palette warm undertone beginner budget'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_tutorials",
        "description": "Пошук туторіалів та технік макіяжу в інтернеті.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Пошуковий запит, напр. 'smokey eye tutorial beginner step by step'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_trends",
        "description": "Пошук актуальних трендів макіяжу та бʼюті.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Пошуковий запит, напр. 'makeup trends 2026 spring'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_profile",
        "description": "Прочитати профіль Ксю — колірний тип, тип шкіри, рівень, продукти які має, преференції.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "update_profile",
        "description": "Оновити профіль Ксю новою інформацією. Використовуй коли дізнаєшся щось нове про неї.",
        "input_schema": {
            "type": "object",
            "properties": {
                "field_path": {
                    "type": "string",
                    "description": "Шлях до поля, напр. 'color_analysis.eye_color' або 'makeup.want_to_learn'"
                },
                "value": {
                    "description": "Нове значення для поля"
                }
            },
            "required": ["field_path", "value"]
        }
    },
    {
        "name": "read_pinterest",
        "description": "Прочитати аналіз Pinterest-борду Ксю щоб зрозуміти її естетичні вподобання.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "analyze_photo",
        "description": "Детально проаналізувати фото для колірного аналізу, оцінки макіяжу, або визначення типу зовнішності.",
        "input_schema": {
            "type": "object",
            "properties": {
                "purpose": {
                    "type": "string",
                    "enum": ["color_analysis", "makeup_evaluation", "look_suggestion", "general"],
                    "description": "Мета аналізу фото"
                }
            },
            "required": ["purpose"]
        }
    }
]


def _web_search(query: str) -> str:
    """Виконує web search через Anthropic API з tool_use."""
    try:
        ai = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = ai.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": f"Search the web and summarize findings: {query}"}],
        )
        # Збираємо всі текстові блоки з відповіді
        texts = []
        for block in resp.content:
            if hasattr(block, "text"):
                texts.append(block.text)
        return "\\n".join(texts) if texts else "Нічого не знайдено."
    except Exception as e:
        logger.error(f"web_search error: {e}")
        return f"Помилка пошуку: {e}"


def _read_profile() -> dict:
    """Читає профіль Ксю."""
    try:
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _update_profile(field_path: str, value) -> str:
    """Оновлює поле в профілі."""
    try:
        profile = _read_profile()
        keys = field_path.split(".")
        obj = profile
        for k in keys[:-1]:
            obj = obj.setdefault(k, {})

        last_key = keys[-1]
        # Якщо поточне значення — список і нове — теж, мерджимо
        if isinstance(obj.get(last_key), list) and isinstance(value, list):
            existing = obj[last_key]
            for item in value:
                if item not in existing:
                    existing.append(item)
            obj[last_key] = existing
        else:
            obj[last_key] = value

        PROFILE_PATH.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"Оновлено {field_path}"
    except Exception as e:
        return f"Помилка оновлення: {e}"


def _read_pinterest() -> str:
    """Читає Pinterest аналіз."""
    p = DATA_DIR / "pinterest_analysis.json"
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        return json.dumps(data, ensure_ascii=False, indent=2)[:3000]
    return "Pinterest аналіз ще не зроблено."


def _execute_tool(name: str, input_data: dict, images: list = None) -> str:
    """Виконує tool і повертає результат як текст."""
    if name == "search_products":
        return _web_search(input_data["query"] + " review quality long-lasting doesn't crease")
    elif name == "search_tutorials":
        return _web_search(input_data["query"])
    elif name == "search_trends":
        return _web_search(input_data["query"])
    elif name == "read_profile":
        profile = _read_profile()
        return json.dumps(profile, ensure_ascii=False, indent=2)
    elif name == "update_profile":
        return _update_profile(input_data["field_path"], input_data["value"])
    elif name == "read_pinterest":
        return _read_pinterest()
    elif name == "analyze_photo":
        return f"Аналізую фото з метою: {input_data.get('purpose', 'general')}. Фото вже в контексті."
    else:
        return f"Невідомий tool: {name}"


class GarciaBrain:
    """
    Agentic reasoning loop для Garcia.

    Отримує повідомлення (текст + можливо фото) і проходить цикл:
    think → use tools → observe → respond

    Використовує Claude з tools для прийняття рішень.
    """

    def __init__(self):
        self.ai = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = "claude-sonnet-4-20250514"
        self.conversation_history: list = []
        self._cost_tracker = {"input_tokens": 0, "output_tokens": 0, "steps": 0}
        self._last_tools = []

    def _build_system(self) -> str:
        """Збирає системний промпт з профілем."""
        profile = _read_profile()
        profile_summary = ""

        ca = profile.get("color_analysis", {})
        if ca.get("skin_tone"):
            profile_summary += f"\\nКолірний аналіз Ксю: скінтон {ca['skin_tone']}, підтон {ca.get('skin_undertone', '?')}, очі {ca.get('eye_color', '?')}, волосся {ca.get('hair_color', '?')}, сезонний тип: {ca.get('season_type', 'не визначено')}."
        if ca.get("best_colors"):
            profile_summary += f"\\nНайкращі кольори: {', '.join(ca['best_colors'])}."

        skin = profile.get("skin", {})
        if skin.get("type"):
            profile_summary += f"\\nТип шкіри: {skin['type']}."
        if skin.get("concerns"):
            profile_summary += f" Проблеми: {', '.join(skin['concerns'])}."

        mu = profile.get("makeup", {})
        profile_summary += f"\\nРівень макіяжу: {mu.get('level', 'beginner')}."
        if mu.get("want_to_learn"):
            profile_summary += f" Хоче вивчити: {', '.join(mu['want_to_learn'])}."
        if mu.get("favorite_looks"):
            profile_summary += f" Улюблені образи: {', '.join(mu['favorite_looks'])}."

        products = profile.get("products", {})
        if products.get("owned"):
            profile_summary += f"\\nМає в косметичці: {', '.join(products['owned'][:10])}."
        if products.get("favorites"):
            profile_summary += f" Улюблені продукти: {', '.join(products['favorites'])}."

        system = GARCIA_PERSONA
        if profile_summary:
            system += f"\\n\\n## Що ти знаєш про Ксю зараз\\n{profile_summary}"

        return system

    def _is_simple_message(self, text: str) -> bool:
        """Визначає чи повідомлення просте (не потребує tools)."""
        t = text.lower().strip()
        # Привітання, подяки, короткі фрази
        simple_patterns = [
            "привіт", "хай", "здоров", "добрий", "доброго",
            "дякую", "дякую!", "спасибі", "спс", "дяки",
            "як справи", "як ти", "що нового",
            "ок", "окей", "добре", "зрозуміла", "круто", "супер",
            "бай", "бувай", "до побачення", "на все", "поки",
        ]
        if any(t.startswith(p) or t == p for p in simple_patterns):
            return True
        # Дуже короткі повідомлення (до 15 символів) без питальних слів
        if len(t) < 15 and "?" not in t and "який" not in t and "яка" not in t and "порад" not in t:
            return True
        return False

    def _fast_reply(self, system: str, messages: list) -> str:
        """Швидка відповідь без tools — один виклик Claude."""
        try:
            resp = self.ai.messages.create(
                model=self.model,
                max_tokens=512,
                system=system,
                messages=messages,
            )
            if hasattr(resp, "usage"):
                self._cost_tracker["input_tokens"] += resp.usage.input_tokens
                self._cost_tracker["output_tokens"] += resp.usage.output_tokens
                self._cost_tracker["steps"] += 1

            final_text = ""
            for block in resp.content:
                if hasattr(block, "text"):
                    final_text += block.text

            self.conversation_history.append({"role": "assistant", "content": final_text})

            cost_in = self._cost_tracker["input_tokens"] * 3 / 1_000_000
            cost_out = self._cost_tracker["output_tokens"] * 15 / 1_000_000
            _append_log({
                "user_message": messages[-1]["content"][-1]["text"][:200] if isinstance(messages[-1]["content"], list) else str(messages[-1]["content"])[:200],
                "has_photo": False,
                "steps": 1,
                "tools_used": ["fast_path"],
                "input_tokens": self._cost_tracker["input_tokens"],
                "output_tokens": self._cost_tracker["output_tokens"],
                "cost_usd": round(cost_in + cost_out, 6),
                "response_len": len(final_text),
            })
            logger.info(f"Fast path: {self._cost_tracker['input_tokens']}in/{self._cost_tracker['output_tokens']}out")
            return final_text
        except Exception as e:
            logger.error(f"Fast reply error: {e}")
            return "Вибач, щось пішло не так 💛"

    def run(self, user_message: str, image_data: list = None) -> str:
        """
        Головний agentic loop.

        Args:
            user_message: текст від Ксю
            image_data: список dict з base64 зображеннями

        Returns:
            Фінальна відповідь Garcia
        """
        system = self._build_system()
        self._last_tools = []

        # Збираємо user content
        content = []
        if image_data:
            for img in image_data:
                content.append(img)
        content.append({"type": "text", "text": user_message})

        # Додаємо в історію розмови
        self.conversation_history.append({"role": "user", "content": content})

        # Тримаємо історію компактною — останні 10 пар
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        # Fast path — прості повідомлення без фото відповідаємо без tools
        if not image_data and self._is_simple_message(user_message):
            return self._fast_reply(system, list(self.conversation_history))

        # Agentic loop
        messages = list(self.conversation_history)

        for step in range(MAX_STEPS):
            self._cost_tracker["steps"] += 1

            try:
                resp = self.ai.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=system,
                    tools=TOOLS_SCHEMA,
                    messages=messages,
                )
            except Exception as e:
                logger.error(f"Brain step {step} error: {e}")
                return "Вибач, щось пішло не так. Спробуй ще раз! 💛"

            # Трекаємо витрати
            if hasattr(resp, "usage"):
                self._cost_tracker["input_tokens"] += resp.usage.input_tokens
                self._cost_tracker["output_tokens"] += resp.usage.output_tokens
            logger.info(f"Brain step {step}: stop_reason={resp.stop_reason}, blocks={[b.type for b in resp.content]}")

            # Якщо stop_reason == "end_turn" — Garcia готова відповісти
            if resp.stop_reason == "end_turn":
                final_text = ""
                for block in resp.content:
                    if hasattr(block, "text"):
                        final_text += block.text
                    logger.info(f"Brain block type={block.type}, has_text={hasattr(block, 'text')}, text_len={len(block.text) if hasattr(block, 'text') else 0}")
                # Зберігаємо відповідь в історію
                self.conversation_history.append({"role": "assistant", "content": final_text})
                logger.info(f"Brain finished in {step + 1} steps, "
                           f"tokens: {self._cost_tracker['input_tokens']}in/"
                           f"{self._cost_tracker['output_tokens']}out")
                # Логуємо взаємодію
                cost_in = self._cost_tracker["input_tokens"] * 3 / 1_000_000
                cost_out = self._cost_tracker["output_tokens"] * 15 / 1_000_000
                _append_log({
                    "user_message": user_message[:200],
                    "has_photo": bool(image_data),
                    "steps": step + 1,
                    "tools_used": self._last_tools,
                    "input_tokens": self._cost_tracker["input_tokens"],
                    "output_tokens": self._cost_tracker["output_tokens"],
                    "cost_usd": round(cost_in + cost_out, 6),
                    "response_len": len(final_text),
                })
                return final_text

            # Якщо stop_reason == "tool_use" — Garcia хоче використати tool
            if resp.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": resp.content})

                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        logger.info(f"Brain tool call: {block.name}({json.dumps(block.input, ensure_ascii=False)[:200]})")
                        self._last_tools.append(block.name)
                        result = _execute_tool(block.name, block.input, images=image_data)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result[:4000]
                        })

                messages.append({"role": "user", "content": tool_results})

        # Якщо вичерпали кроки
        logger.warning(f"Brain hit MAX_STEPS ({MAX_STEPS})")
        return "Хм, занадто складне питання — давай розібʼємо на частини? 🤔"

    def get_cost_summary(self) -> str:
        """Повертає зведення витрат поточної сесії."""
        t = self._cost_tracker
        cost_in = t["input_tokens"] * 3 / 1_000_000
        cost_out = t["output_tokens"] * 15 / 1_000_000
        total = cost_in + cost_out
        return (f"📊 Сесія: {t['steps']} кроків, "
                f"{t['input_tokens']}+{t['output_tokens']} токенів, "
                f"~${total:.4f}")

    def reset_history(self):
        """Очищає історію розмови."""
        self.conversation_history = []
        self._cost_tracker = {"input_tokens": 0, "output_tokens": 0, "steps": 0}
