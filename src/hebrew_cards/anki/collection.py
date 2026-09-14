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


# Anki stores a card's flag in the low three bits of `cards.flags`.
FLAG_NONE = 0
FLAG_RED = 1
FLAG_GREEN = 3

FLAG_NAMES = {FLAG_NONE: "none", FLAG_RED: "red", FLAG_GREEN: "green"}


@dataclass(frozen=True)
class RawNote:
    """One note as stored, before any interpretation."""

    nid: int
    deck: str
    notetype: str
    fields: tuple[str, ...]
    tags: str
    guid: str = ""
    # Flags live on cards, not notes. A note's flag is the first non-zero flag among
    # its cards, since the owner flags whichever card surfaced the problem.
    flag: int = FLAG_NONE


def copy_collection(destination: Path, source: Path = DEFAULT_COLLECTION) -> Path:
    """Copy the collection to `destination` and return the new path.

    Copying rather than opening in place is deliberate: Anki may be running, and a
    read-only promise is easier to keep when the file is not the real one.

    The sidecar files must come too. Anki runs SQLite in write-ahead-log mode, so
    while it is open, recent changes live in `collection.anki2-wal` and not in the
    main database — which can lag by any amount of time. Copying the `.anki2` alone
    yields a stale snapshot that looks perfectly valid: it silently reported decks
    the owner had already deleted, and missed an import they had already done.
    """
    if not source.exists():
        raise FileNotFoundError(f"Anki collection not found at {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    for suffix in ("-wal", "-shm"):
        sidecar = source.with_name(source.name + suffix)
        if sidecar.exists():
            shutil.copy2(sidecar, destination.with_name(destination.name + suffix))
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


def read_notes(collection_copy: Path, *, generated: bool = False) -> list[RawNote]:
    """Return `Modern Hebrew::*` notes from the collection copy.

    By default this yields only *source* notes: in the `Modern Hebrew` tree, and not
    produced by this pipeline.

    Pass `generated=True` to read the notes this pipeline produced instead, which is
    what the review-harvest flow needs. Those are matched by note marker alone, with
    no deck restriction — a generated note is generated wherever it sits, and it may
    legitimately sit outside the `Modern Hebrew` tree (under a staging root during a
    migration, or anywhere the owner has moved it). Requiring a deck match here once
    made harvest silently find nothing.
    """
    # Opened read-write, deliberately: this is a disposable copy, and SQLite must be
    # able to replay the write-ahead log to see the collection's current state. The
    # live collection is never opened at all — that is what copy_collection() is for.
    conn = sqlite3.connect(collection_copy)
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
        note_flag: dict[int, int] = {}
        for did, nid, flags in conn.execute("select did, nid, flags from cards"):
            note_deck.setdefault(nid, decks.get(did, "?"))
            flag = flags & 7
            if flag and not note_flag.get(nid):
                note_flag[nid] = flag

        notes: list[RawNote] = []
        query = "select id, mid, flds, tags, guid from notes"
        for nid, mid, flds, tags, guid in conn.execute(query):
            deck = note_deck.get(nid, "?")
            notetype = notetypes.get(mid, "?")
            if is_generated(notetype, tags) != generated:
                continue
            if not generated and not in_scope(deck):
                continue
            notes.append(
                RawNote(
                    nid=nid,
                    deck=deck,
                    notetype=notetype,
                    fields=tuple(flds.split(FIELD_SEP)),
                    tags=tags,
                    guid=guid,
                    flag=note_flag.get(nid, FLAG_NONE),
                )
            )
        return notes
    finally:
        conn.close()
