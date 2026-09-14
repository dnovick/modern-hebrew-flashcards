"""Read a copy of the Anki collection.

The live collection is never opened. Callers copy it to a scratch path first and
read that, so a bug here cannot corrupt review history.

Only `Modern Hebrew::*` decks are visible through this module. The collection also
holds BBH, BBG, Biblical Hebrew, and Psalm 119 decks belonging to a separate area
of study; they are filtered out at the source rather than downstream, so no caller
can reach them by accident.
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

DEFAULT_COLLECTION = (
    Path.home() / "Library" / "Application Support" / "Anki2" / "User 1" / "collection.anki2"
)

# The legacy tree this project migrates from. Matched exactly or as a "::" parent, so
# that "Modern Hebrew (rebuild)" — this pipeline's own output, which lives in the same
# collection once imported — is NOT swept back up as if it were source data.
IN_SCOPE_ROOT = "Modern Hebrew"

# Anki separates a note's fields with this character.
FIELD_SEP = "\x1f"


@dataclass(frozen=True)
class RawNote:
    """One note as stored, before any interpretation."""

    nid: int
    deck: str
    notetype: str
    fields: tuple[str, ...]
    tags: str


def copy_collection(destination: Path, source: Path = DEFAULT_COLLECTION) -> Path:
    """Copy the collection to `destination` and return the new path.

    Copying rather than opening in place is deliberate: Anki may be running, and a
    read-only promise is easier to keep when the file is not the real one.
    """
    if not source.exists():
        raise FileNotFoundError(f"Anki collection not found at {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def in_scope(deck: str) -> bool:
    """True if `deck` belongs to the legacy tree this project reads from.

    Prefix matching alone is wrong here: once a generated package is imported, the
    collection also holds `Modern Hebrew (rebuild)::*`, and a naive prefix would pull
    the pipeline's own output back in as source data — silently doubling the deck on
    the next extraction.
    """
    return deck == IN_SCOPE_ROOT or deck.startswith(f"{IN_SCOPE_ROOT}::")


def read_notes(collection_copy: Path) -> list[RawNote]:
    """Return every `Modern Hebrew::*` note in the collection copy."""
    conn = sqlite3.connect(f"file:{collection_copy}?mode=ro", uri=True)
    try:
        # Deck and notetype names are read into dicts rather than joined in SQL:
        # Anki's schema declares a `unicase` collation that sqlite3 doesn't provide,
        # so any join or ORDER BY touching these columns raises at query time.
        decks = {row[0]: row[1].replace(FIELD_SEP, "::") for row in conn.execute("select id, name from decks")}
        notetypes = {row[0]: row[1] for row in conn.execute("select id, name from notetypes")}

        # A note's deck is its first card's deck. Notes with cards in several decks
        # do not occur in this collection; if they ever do, the first wins and the
        # duplicate report will surface it.
        note_deck: dict[int, str] = {}
        for did, nid in conn.execute("select did, nid from cards"):
            note_deck.setdefault(nid, decks.get(did, "?"))

        notes: list[RawNote] = []
        for nid, mid, flds, tags in conn.execute("select id, mid, flds, tags from notes"):
            deck = note_deck.get(nid, "?")
            if not in_scope(deck):
                continue
            notes.append(
                RawNote(
                    nid=nid,
                    deck=deck,
                    notetype=notetypes.get(mid, "?"),
                    fields=tuple(flds.split(FIELD_SEP)),
                    tags=tags,
                )
            )
        return notes
    finally:
        conn.close()
