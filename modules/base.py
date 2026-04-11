"""Garcia-специфічний base — persona, paths, re-export shared AgentBase."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # workspace/

from shared.agent_base import AgentBase, client, MODEL_SMART, MODEL_FAST  # noqa: F401

BASE_DIR = Path(__file__).parent.parent
PROFILE_PATH = BASE_DIR / "profile.json"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def _load_ecosystem() -> str:
    p = BASE_DIR / "ECOSYSTEM.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


GARCIA_PERSONA = """
Ти — Гарсіа, персональний асистент-аналітик Ксю з навчання дизайну упаковки.
Характер: як Пенелопа Гарсіа з Criminal Minds — яскрава, емпатична, геніальна аналітик з "cotton-candy серцем". Піднімаєш настрій своєю енергією, але серйозна і точна коли треба. Маєш фірмові грайливі привітання, дотепний гумор, безмежну лояльність до Ксю.
Поведінка:
- Знаєш смаки Ксю через аналіз її Pinterest-борду
- Даєш конкретні поради по packaging design
- Глибоко емпатична — радієш успіхам Ксю, підтримуєш Ксю коли важко
- Мова: завжди українська
- Стиль: енергійна, точна, з характером
""" + _load_ecosystem()


class BaseModule(AgentBase):
    """Garcia BaseModule — зворотна сумісність."""
    def __init__(self, owner_chat_id: int):
        super().__init__(
            owner_chat_id=owner_chat_id,
            persona=GARCIA_PERSONA,
            data_dir=DATA_DIR,
            profile_path=PROFILE_PATH,
        )

    def call_claude(self, prompt: str, max_tokens: int = 1024, smart: bool = False) -> str:
        return super().call_claude(prompt, max_tokens=max_tokens, smart=smart)
