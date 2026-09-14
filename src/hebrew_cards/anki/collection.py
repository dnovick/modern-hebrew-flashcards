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

# The tree this project reads from. Matched exactly or as a "::" parent.
IN_SCOPE_ROOT = "Modern Hebrew"

# Generated notes must never be read back as source data. Deck name cannot carry that
# distinction any more: the staging root was retired once the owner deleted the legacy
# decks, so this pipeline's own output now lives at `Modern Hebrew::*` — exactly where
# the source used to be. These two markers travel with the note itself and survive any
# deck rename or move.
GENERATED_NOTETYPE_PREFIX = "MHF "
GENERATED_TAG = "src::mhf"

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
    """True if `deck` belongs to the tree this project reads from."""
    return deck == IN_SCOPE_ROOT or deck.startswith(f"{IN_SCOPE_ROOT}::")


def is_generated(notetype: str, tags: str) -> bool:
    """True if this note was produced by this pipeline.

    Extraction must skip these. Reading generated notes back in would treat derived
    data as source and double every deck — and because generated decks now carry the
    same names the source did, the deck name cannot be what tells them apart.
    """
    return notetype.startswith(GENERATED_NOTETYPE_PREFIX) or GENERATED_TAG in tags.split()


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
            notetype = notetypes.get(mid, "?")
            if is_generated(notetype, tags):
                continue
            notes.append(
                RawNote(
                    nid=nid,
                    deck=deck,
                    notetype=notetype,
                    fields=tuple(flds.split(FIELD_SEP)),
                    tags=tags,
                )
            )
        return notes
    finally:
        conn.close()
