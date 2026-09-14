"""Harvest review decisions made in Anki back into the deck YAML.

The YAML is the source of truth, so an edit made in Anki's editor is normally lost
on the next rebuild. That makes reviewing flagged entries awkward: the natural place
to look at a card is Anki, and the natural place to fix it is the field right there.

This module closes that loop. The owner reviews in Anki and records a verdict with a
card flag; this reads those verdicts, along with any edits made alongside them, and
writes them into the YAML. Anki is still not the source of truth — it is an input to
a deliberate, reported, reviewable harvest.

    green flag  the entry is correct as it now stands in Anki
                -> adopt any edit, clear needs_review
    red flag    still wrong, or edited but not finished
                -> adopt any edit, keep needs_review
    no flag     untouched; left exactly as it is
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .anki.collection import FLAG_GREEN, FLAG_NONE, FLAG_RED, RawNote
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

    @property
    def edited(self) -> bool:
        return self.new_hebrew is not None and self.new_hebrew != self.old_hebrew


@dataclass
class HarvestResult:
    changes: list[Change] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)

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


def harvest(
    decks: list[tuple[Path, DeckFile]],
    notes: list[RawNote],
    citation_field: int = 0,
) -> HarvestResult:
    """Apply flag verdicts and field edits from `notes` onto `decks`, in place."""
    index = index_by_guid(decks)
    result = HarvestResult()

    for note in notes:
        if note.flag == FLAG_NONE:
            continue
        found = index.get(note.guid)
        if found is None:
            result.unmatched.append(f"{note.deck}: nid={note.nid} (guid not in any deck file)")
            continue
        _, deck, entry = found

        old = _citation(entry)
        new = note.fields[citation_field].strip() if len(note.fields) > citation_field else ""
        change = Change(
            deck=deck.meta.name,
            entry_id=entry.id,
            verdict="approved" if note.flag == FLAG_GREEN else "still flagged",
            old_hebrew=old,
            new_hebrew=new or None,
        )

        if change.edited and new:
            _set_citation(entry, new)

        if note.flag == FLAG_GREEN:
            entry.needs_review = False
            entry.review_notes = []
        elif note.flag == FLAG_RED:
            entry.needs_review = True

        result.changes.append(change)

    return result
