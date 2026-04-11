"""Garcia catchup — ретроспектива packaging design новин."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.catchup_module import CatchupModule as _CatchupModule
from .base import GARCIA_PERSONA, DATA_DIR, PROFILE_PATH


class CatchupModule(_CatchupModule):
    catchup_topics = """- packaging design trends and innovations
- sustainable eco-friendly packaging materials
- luxury brand packaging releases
- botanical floral minimalist design trends
- packaging design awards and case studies"""
    catchup_domain = "packaging design новин"

    def __init__(self, owner_chat_id: int):
        super().__init__(
            owner_chat_id=owner_chat_id,
            persona=GARCIA_PERSONA,
            data_dir=DATA_DIR,
            profile_path=PROFILE_PATH,
        )
