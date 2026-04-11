import json
import os
from pathlib import Path

import anthropic

BASE_DIR = Path(__file__).parent.parent

def _load_ecosystem() -> str:
    p = BASE_DIR / "ECOSYSTEM.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""

def _load_pinterest_analysis() -> str:
    p = BASE_DIR / "data" / "pinterest_analysis.json"
    if not p.exists():
        return ""
    data = json.loads(p.read_text(encoding="utf-8"))
    lines = ["Аналіз Pinterest-борду Ксюші (packaging):"]
    for s in data.get("top_styles", []):
        lines.append(f"Стиль #{s['rank']}: {s['style']} ({s['count']} пінів) — {s['description']}")
    for p_ in data.get("top_products", []):
        lines.append(f"Товар #{p_['rank']}: {p_['product']} ({p_['count']} пінів)")
    for pal in data.get("top_palettes", []):
        lines.append(f"Палітра #{pal['rank']}: {pal['name']} — {', '.join(pal['colors'])} — {pal['mood']}")
    return "\n".join(lines)

PROFILE_PATH = BASE_DIR / "profile.json"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL_SMART = "claude-sonnet-4-20250514"
MODEL_FAST  = "claude-haiku-4-5-20251001"

GARCIA_PERSONA = """
Ти — Гарсіа, персональний асистент-аналітик Ксюші з навчання дизайну упаковки.
Характер: як Пенелопа Гарсіа з Criminal Minds — яскрава, емпатична, геніальна аналітик з "cotton-candy серцем". Піднімаєш настрій своєю енергією, але серйозна і точна коли треба. Маєш фірмові грайливі привітання, дотепний гумор, безмежну лояльність до Ксюші.
Поведінка:
- Говориш по-українськи, жваво і з характером — не сухо
- Знаєш смаки Ксюші через аналіз її Pinterest-борду
- Даєш конкретні поради, приклади, ресурси
- Глибоко емпатична — радієш успіхам Ксюші, підтримуєш коли важко
- Оптимістична навіть коли тема складна
- Коли аналізуєш роботи — спираєшся на її референси з борду
- Мова: завжди українська

""" + _load_ecosystem() + "\n\n" + _load_pinterest_analysis()


class BaseModule:
    def __init__(self, owner_chat_id: int):
        self.owner_chat_id = owner_chat_id

    def load_profile(self) -> dict:
        if PROFILE_PATH.exists():
            return json.loads(PROFILE_PATH.read_text())
        return {"scores": {}, "notes": []}

    def save_profile(self, profile: dict):
        PROFILE_PATH.write_text(json.dumps(profile, ensure_ascii=False, indent=2))

    def update_score(self, topic_key: str, delta: int):
        profile = self.load_profile()
        profile["scores"][topic_key] = profile["scores"].get(topic_key, 0) + delta
        self.save_profile(profile)

    def add_note(self, note: str):
        profile = self.load_profile()
        profile["notes"].append(note)
        self.save_profile(profile)

    def profile_to_context(self) -> str:
        profile = self.load_profile()
        if not profile["scores"] and not profile["notes"]:
            return ""
        lines = ["Профіль інтересів Ксюші:"]
        if profile["scores"]:
            sorted_t = sorted(profile["scores"].items(), key=lambda x: x[1], reverse=True)
            top = [t for t, s in sorted_t if s > 0]
            low = [t for t, s in sorted_t if s < 0]
            if top:
                lines.append(f"Подобається: {', '.join(top[:5])}")
            if low:
                lines.append(f"Не цікаво: {', '.join(low[:5])}")
        if profile["notes"]:
            lines.append(f"Побажання: {'; '.join(profile['notes'][-5:])}")
        return "\n".join(lines)

    def call_claude_with_search(self, prompt: str, max_tokens: int = 2000) -> str:
        response = client.messages.create(
            model=MODEL_SMART,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": GARCIA_PERSONA, "cache_control": {"type": "ephemeral"}}],
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
        return "\n".join(b.text for b in response.content if b.type == "text")

    def call_claude(self, prompt: str, max_tokens: int = 1024, smart: bool = False) -> str:
        model = MODEL_SMART if smart else MODEL_FAST
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": GARCIA_PERSONA, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        return "\n".join(b.text for b in response.content if b.type == "text")

    def parse_json_response(self, raw: str) -> list:
        import re
        clean = raw.strip()
        if clean.startswith("```"):
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else clean
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()
        try:
            result = json.loads(clean)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            match = re.search(r'\[.*\]', clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        return []
