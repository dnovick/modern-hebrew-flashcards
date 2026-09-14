"""Assemble deck YAML into an Anki package.

Builds are deterministic: note GUIDs, note type ids, and deck ids all derive from
stable keys, so rebuilding unchanged data produces a package that updates existing
notes in place rather than duplicating them.

Output is always a `.apkg` file. This module never touches the live collection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import genanki

from .ids import note_guid, stable_id
from .models import DeckFile, Entry
from .notetypes import model_for

# The migration is complete: the owner backed up, deleted both the legacy tree and
# the staging tree, and asked for the real name (2026-09-13). Generated decks are now
# the only `Modern Hebrew` decks in the collection.
DEFAULT_DECK_ROOT = "Modern Hebrew"

PROVENANCE_TAG = "src::mhf"


@dataclass
class BuildStats:
    """What a build produced, for reporting."""

    decks: int = 0
    notes: int = 0
    skipped: list[str] = field(default_factory=list)


def _field_values(entry: Entry) -> dict[str, str]:
    """Map an entry onto its note type's fields."""
    forms = entry.forms or {}
    common = {
        "English": entry.english,
        "Audio": entry.audio or "",
        "Notes": "",
    }
    if entry.pos == "verb":
        return {
            **common,
            "Lemma": entry.lemma or "",
            "Root": entry.root or "",
            "Binyan": entry.binyan or "",
            "Gizra": entry.gizra or "",
            "Infinitive": entry.infinitive or "",
        }
    if entry.pos == "adjective":
        return {
            **common,
            "Hebrew": entry.hebrew or forms.get("ms", ""),
            "FormMS": forms.get("ms", ""),
            "FormFS": forms.get("fs", ""),
            "FormMP": forms.get("mp", ""),
            "FormFP": forms.get("fp", ""),
        }
    if entry.pos == "noun":
        return {
            **common,
            "Hebrew": entry.hebrew or "",
            "Gender": entry.gender or "",
            "Plural": entry.plural or "",
            "PluralAudio": "",
        }
    return {**common, "Hebrew": entry.hebrew or ""}


def _tags(entry: Entry) -> list[str]:
    tags = [PROVENANCE_TAG, f"pos::{entry.pos}"]
    if entry.binyan:
        tags.append(f"binyan::{entry.binyan}")
    if entry.gender:
        tags.append(f"gender::{entry.gender}")
    if entry.needs_review:
        tags.append("needs-review")
    tags.extend(entry.tags)
    # Anki tags cannot contain spaces.
    return sorted({t.replace(" ", "-") for t in tags})


def build_note(entry: Entry, deck_slug: str) -> genanki.Note:
    """Build one Anki note from one entry."""
    model = model_for(entry.pos)
    values = _field_values(entry)
    ordered = [values.get(f["name"], "") for f in model.fields]
    return genanki.Note(
        model=model,
        fields=ordered,
        tags=_tags(entry),
        guid=note_guid(deck_slug, entry.id),
        sort_field=0,
    )


def build_deck(deck: DeckFile, deck_slug: str, deck_root: str) -> tuple[genanki.Deck, int]:
    """Build one genanki deck. Returns the deck and how many notes it holds."""
    name = f"{deck_root}::{deck.meta.name}"
    anki_deck = genanki.Deck(deck_id=stable_id(name), name=name)
    for entry in deck.entries:
        anki_deck.add_note(build_note(entry, deck_slug))
    return anki_deck, len(deck.entries)


def build_package(
    decks: list[tuple[Path, DeckFile]],
    output: Path,
    deck_root: str = DEFAULT_DECK_ROOT,
) -> BuildStats:
    """Build every deck into a single `.apkg` at `output`."""
    stats = BuildStats()
    anki_decks: list[genanki.Deck] = []
    for path, deck in decks:
        if not deck.entries:
            stats.skipped.append(f"{path.name} (no entries)")
            continue
        anki_deck, count = build_deck(deck, path.stem, deck_root)
        anki_decks.append(anki_deck)
        stats.decks += 1
        stats.notes += count

    output.parent.mkdir(parents=True, exist_ok=True)
    genanki.Package(anki_decks).write_to_file(str(output))
    return stats
