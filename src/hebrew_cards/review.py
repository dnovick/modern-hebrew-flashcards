"""Harvest review decisions made in Anki back into the deck YAML.

The YAML is the source of truth, so an edit made in Anki's editor is normally lost
on the next rebuild. That makes reviewing flagged entries awkward: the natural place
to look at a card is Anki, and the natural place to fix it is the field right there.

This module closes that loop. The owner reviews in Anki and records a verdict with a
card flag; this reads those verdicts, along with any edits made alongside them, and
writes them into the YAML. Anki is still not the source of truth — it is an input to
a deliberate, reported, reviewable harvest.

    green flag   the entry is correct as it now stands in Anki
                 -> adopt any edit, clear needs_review
    orange flag  this entry should not exist — a duplicate, or misfiled
                 -> delete it from the YAML
    red flag     still wrong, or edited but not finished
                 -> adopt any edit, keep needs_review
    no flag      untouched; left exactly as it is

Deleting a note in Anki alone does not work: the YAML is what builds the deck, so the
next import recreates it. Deletion has to happen in the source, which is what the
orange flag is for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .anki.collection import FLAG_GREEN, FLAG_NONE, FLAG_ORANGE, FLAG_RED, RawNote
from .ids import note_guid
from .models import DeckFile, Entry


@dataclass
class Change:
    """One harvested decision, for reporting."""

    deck: str
    entry_id: str
    verdict: str
    old_hebrew: str | None = None
    new_hebrew: str | None = None
    old_english: str | None = None
    new_english: str | None = None

    @property
    def hebrew_edited(self) -> bool:
        return bool(self.new_hebrew) and self.new_hebrew != self.old_hebrew

    @property
    def english_edited(self) -> bool:
        return bool(self.new_english) and self.new_english != self.old_english

    @property
    def edited(self) -> bool:
        return self.hebrew_edited or self.english_edited


@dataclass
class Orphan:
    """A generated note in Anki with no entry behind it any more."""

    deck: str
    nid: int
    hebrew: str
    english: str


@dataclass
class HarvestResult:
    changes: list[Change] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    deleted: list[Change] = field(default_factory=list)

    @property
    def approved(self) -> int:
        return sum(1 for c in self.changes if c.verdict == "approved")

    @property
    def edits(self) -> int:
        return sum(1 for c in self.changes if c.edited)


def _citation(entry: Entry) -> str:
    return entry.hebrew or entry.lemma or ""


def _set_citation(entry: Entry, value: str) -> None:
    if entry.lemma is not None:
        entry.lemma = value
    else:
        entry.hebrew = value
    if entry.forms and "ms" in entry.forms:
        entry.forms["ms"] = value


def index_by_guid(decks: list[tuple[Path, DeckFile]]) -> dict[str, tuple[Path, DeckFile, Entry]]:
    """Map every entry's note GUID back to the entry itself."""
    index: dict[str, tuple[Path, DeckFile, Entry]] = {}
    for path, deck in decks:
        for entry in deck.entries:
            index[note_guid(path.stem, entry.id)] = (path, deck, entry)
    return index


# Field positions shared by every MHF note type: the citation form first, the gloss
# second. Both are harvested, because a flagged entry is as likely to have a wrong
# gloss as wrong pointing — several are flagged precisely for a gloss collision.
CITATION_FIELD = 0
ENGLISH_FIELD = 1


def _field(note: RawNote, index: int) -> str:
    return note.fields[index].strip() if len(note.fields) > index else ""


def find_orphans(
    decks: list[tuple[Path, DeckFile]],
    notes: list[RawNote],
) -> list[Orphan]:
    """Generated notes whose entry no longer exists in the YAML.

    Importing a package adds and updates notes; it never deletes them. So when an
    entry is removed from the source — two duplicates merged into one, say — its note
    stays behind in the collection forever, still scheduled, still appearing in
    reviews. Nothing detects that except looking for it, which is what this does.
    Deleting the note is the owner's action, in Anki.
    """
    known = set(index_by_guid(decks))
    return [
        Orphan(
            deck=note.deck,
            nid=note.nid,
            hebrew=_field(note, CITATION_FIELD),
            english=_field(note, ENGLISH_FIELD),
        )
        for note in notes
        if note.guid not in known
    ]


def harvest(
    decks: list[tuple[Path, DeckFile]],
    notes: list[RawNote],
) -> HarvestResult:
    """Apply flag verdicts and field edits from `notes` onto `decks`, in place."""
    index = index_by_guid(decks)
    result = HarvestResult()
    to_delete: list[tuple[DeckFile, Entry]] = []

    for note in notes:
        if note.flag == FLAG_NONE:
            continue
        found = index.get(note.guid)
        if found is None:
            result.unmatched.append(f"{note.deck}: nid={note.nid} (guid not in any deck file)")
            continue
        _, deck, entry = found

        change = Change(
            deck=deck.meta.name,
            entry_id=entry.id,
            verdict="approved" if note.flag == FLAG_GREEN else "still flagged",
            old_hebrew=_citation(entry),
            new_hebrew=_field(note, CITATION_FIELD) or None,
            old_english=entry.english,
            new_english=_field(note, ENGLISH_FIELD) or None,
        )

        # An empty field is far more likely a slip than an intended deletion, so a
        # blank never overwrites content — hence the `and new_*` guards.
        if change.hebrew_edited and change.new_hebrew:
            _set_citation(entry, change.new_hebrew)
        if change.english_edited and change.new_english:
            entry.english = change.new_english

        if note.flag == FLAG_ORANGE:
            change.verdict = "delete"
            to_delete.append((deck, entry))
            result.deleted.append(change)
            continue

        if note.flag == FLAG_GREEN:
            entry.needs_review = False
            entry.review_notes = []
        elif note.flag == FLAG_RED:
            entry.needs_review = True

        result.changes.append(change)

    # Removal happens after the walk so the deck lists are not mutated mid-iteration.
    for deck, entry in to_delete:
        deck.entries.remove(entry)

    return result
