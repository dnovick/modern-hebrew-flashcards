"""Load and validate deck YAML.

Validation failures are hard errors that name the offending file and entry — a
malformed deck should stop the build, not silently produce a deck missing cards.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import DeckFile


class DeckLoadError(Exception):
    """A deck file could not be read or did not validate."""


def load_deck(path: Path) -> DeckFile:
    """Load one deck YAML file."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DeckLoadError(f"{path.name}: not valid YAML — {exc}") from exc
    if not isinstance(raw, dict):
        raise DeckLoadError(f"{path.name}: expected a mapping at the top level")
    try:
        deck = DeckFile.model_validate(raw)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"])
        raise DeckLoadError(f"{path.name}: {where}: {first['msg']}") from exc

    seen: set[str] = set()
    for entry in deck.entries:
        if entry.id in seen:
            raise DeckLoadError(f"{path.name}: duplicate entry id {entry.id!r}")
        seen.add(entry.id)
    return deck


def load_all(directory: Path) -> list[tuple[Path, DeckFile]]:
    """Load every deck file in `directory`, sorted by filename."""
    paths = sorted(directory.glob("*.yaml"))
    if not paths:
        raise DeckLoadError(f"no deck files found in {directory}")
    return [(path, load_deck(path)) for path in paths]
