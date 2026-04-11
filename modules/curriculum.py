"""Garcia curriculum — план навчання Packaging Design."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.curriculum_engine import CurriculumEngine
from .base import GARCIA_PERSONA, DATA_DIR, PROFILE_PATH

CURRICULUM = [
    {"id": 1, "title": "Основи dieline і розгортки", "estimate": "2-3 дні",
     "why": "Без розуміння розгортки неможливо зробити упаковку — це фундамент всього.",
     "read": "https://www.thepackagingcompany.com/knowledge-center/dieline-design-guide",
     "do": "Скачати безкоштовний dieline коробки з lovelypackage.com і обвести в Illustrator."},
    {"id": 2, "title": "Типографіка для упаковки", "estimate": "2-3 дні",
     "why": "Шрифт на упаковці — це не просто текст, це частина бренду і UX покупця.",
     "read": "https://www.packaging-gateway.com/features/typography-packaging-design/",
     "do": "Взяти один зі своїх botanical референсів і розібрати які шрифти використані і чому."},
    {"id": 3, "title": "Колір і кольорові моделі (CMYK vs RGB)", "estimate": "1-2 дні",
     "why": "Колір на екрані і в друці — різні речі. Помилка коштує грошей клієнту.",
     "read": "https://www.printingforless.com/cmyk-vs-rgb.html",
     "do": "Взяти свою улюблену палітру з Pinterest і конвертувати в CMYK. Порівняти різницю."},
    {"id": 4, "title": "Матеріали і технології друку", "estimate": "2-3 дні",
     "why": "Знання матеріалів відрізняє дизайнера від ілюстратора.",
     "read": "https://www.packaging-gateway.com/features/packaging-materials/",
     "do": "Зібрати 5 прикладів luxury упаковки і визначити матеріал та технологію друку кожної."},
    {"id": 5, "title": "Botanical стиль: аналіз і практика", "estimate": "3-4 дні",
     "why": "Твій улюблений напрям — час зробити його своєю сильною стороною.",
     "read": "https://www.thedielineawards.com/",
     "do": "Знайти 10 кращих botanical packaging з Dieline Awards і зробити розбір кожного."},
    {"id": 6, "title": "Структура упаковки: коробки, флакони, саші", "estimate": "2-3 дні",
     "why": "Різні форми — різна логіка дизайну і взаємодії з покупцем.",
     "read": "https://lovelypackage.com/",
     "do": "Знайти по 3 приклади кожного типу і описати як форма впливає на сприйняття бренду."},
    {"id": 7, "title": "Hierarchy і композиція на упаковці", "estimate": "2-3 дні",
     "why": "Покупець бачить упаковку 3 секунди — ієрархія вирішує все.",
     "read": "https://www.creativebloq.com/advice/packaging-design-tips",
     "do": "Взяти 5 своїх референсів і накреслити схему ієрархії елементів для кожного."},
]


class GarciaCurriculum(CurriculumEngine):
    notebooklm_context = (
        "Packaging designer learning the craft. Interested in botanical, luxury and minimal aesthetics. "
        "Has good taste from Pinterest research, now building technical skills."
    )
    dynamic_curriculum_prompt = (
        "You are a personalized packaging design curriculum designer. "
        "The learner is a designer interested in botanical, luxury and minimal packaging aesthetics."
    )

    def __init__(self, owner_chat_id: int):
        super().__init__(
            owner_chat_id=owner_chat_id,
            persona=GARCIA_PERSONA,
            data_dir=DATA_DIR,
            profile_path=PROFILE_PATH,
        )
        self.CURRICULUM = CURRICULUM


_instance_cache: dict[int, GarciaCurriculum] = {}

def _get(owner_chat_id: int = 0) -> GarciaCurriculum:
    if owner_chat_id not in _instance_cache:
        _instance_cache[owner_chat_id] = GarciaCurriculum(owner_chat_id)
    return _instance_cache[owner_chat_id]


async def cmd_curriculum(update, context):
    await _get(update.effective_user.id).cmd_curriculum(update, context)

async def cmd_done(update, context):
    await _get(update.effective_user.id).cmd_done(update, context)

async def handle_curriculum_callback(update, context):
    await _get(update.effective_user.id).handle_curriculum_callback(update, context)

def load_state():
    return _get().load_state()
