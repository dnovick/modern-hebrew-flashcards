"""Put src/ on the path so tests import hebrew_cards without an editable install."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
