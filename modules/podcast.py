"""Garcia podcast — packaging design тематика."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.podcast_module import PodcastModule as _PodcastModule
from .base import GARCIA_PERSONA, DATA_DIR, PROFILE_PATH
from .curriculum import CURRICULUM


class GarciaPodcast(_PodcastModule):
    podcast_audience = (
        "Designer learning packaging design. Interested in botanical, luxury and minimal aesthetics. "
        "Has a good eye for design, now building technical knowledge."
    )
    podcast_style = (
        "Reference practical scenarios: dieline construction, typography choices, "
        "color systems for print, material selection, brand hierarchy."
    )

    def __init__(self, owner_chat_id: int):
        super().__init__(
            owner_chat_id=owner_chat_id,
            persona=GARCIA_PERSONA,
            data_dir=DATA_DIR,
            profile_path=PROFILE_PATH,
        )
        self.CURRICULUM = CURRICULUM


_podcast_instance: dict[int, GarciaPodcast] = {}

def _get(owner_chat_id: int = 0) -> GarciaPodcast:
    if owner_chat_id not in _podcast_instance:
        _podcast_instance[owner_chat_id] = GarciaPodcast(owner_chat_id)
    return _podcast_instance[owner_chat_id]

async def cmd_podcast(update, context):
    await _get(update.effective_user.id).cmd_podcast(update, context)
