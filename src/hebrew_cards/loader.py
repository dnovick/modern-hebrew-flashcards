"""Load and validate deck YAML.

Validation failures are hard errors that name the offending file and entry — a
malformed deck should stop the build, not silently produce a deck missing cards.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from . import hebrew
from .models import DeckFile, Entry


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
        _normalize_hebrew(entry)
        _check_hebrew(path, entry)
    return deck


def _normalize_hebrew(entry: Entry) -> None:
    """NFC-normalize every Hebrew field.

    Combining marks have a canonical order — dagesh (class 21) precedes patach
    (class 33) — and hand-editing YAML can easily produce them the other way round,
    which renders inconsistently across fonts and breaks equality comparisons against
    otherwise identical text. Normalizing on load rather than on write means
    externally-edited files are handled the same as generated ones.
    """
    for field_name in ("hebrew", "lemma", "plural", "infinitive", "governs"):
        value = getattr(entry, field_name)
        if value:
            setattr(entry, field_name, hebrew.normalize(value))
    if entry.forms:
        entry.forms = {k: hebrew.normalize(v) for k, v in entry.forms.items()}


def _check_hebrew(path: Path, entry: Entry) -> None:
    """Reject Hebrew that is structurally invalid.

    A combining mark before the first letter has no valid reading — it is always
    corruption, usually a furtive patach detached from a final guttural (תַפּוּחַ
    arriving as ַתַפּוּח). Three entries reached the first built deck that way, so this
    fails the build rather than letting it happen again.
    """
    candidates = [entry.hebrew, entry.lemma, entry.plural, entry.infinitive]
    candidates.extend((entry.forms or {}).values())
    for value in candidates:
        if value and hebrew.is_point(value[0]):
            raise DeckLoadError(
                f"{path.name}: entry {entry.id!r}: {value!r} begins with a combining "
                f"mark, which is never valid — a vowel has come detached from its letter"
            )


def load_all(directory: Path) -> list[tuple[Path, DeckFile]]:
    """Load every deck file in `directory`, sorted by filename."""
    paths = sorted(directory.glob("*.yaml"))
    if not paths:
        raise DeckLoadError(f"no deck files found in {directory}")
    return [(path, load_deck(path)) for path in paths]
