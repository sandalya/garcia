"""Garcia digest — packaging design новини."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.digest_module import DigestModule as _DigestModule
from .base import GARCIA_PERSONA, DATA_DIR, PROFILE_PATH


class DigestModule(_DigestModule):
    topics = [
        "packaging design trends 2025",
        "sustainable packaging materials innovation",
        "luxury brand packaging new releases",
        "botanical floral packaging design",
        "packaging design awards winners",
        "Dieline packaging design news",
    ]
    digest_label = "Packaging Design"
    overview_style = "як Гарсіа: енергійно, з характером, конкретно"

    def __init__(self, owner_chat_id: int):
        super().__init__(
            owner_chat_id=owner_chat_id,
            persona=GARCIA_PERSONA,
            data_dir=DATA_DIR,
            profile_path=PROFILE_PATH,
        )
