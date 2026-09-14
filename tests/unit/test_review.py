"""Tests for harvesting review decisions from Anki back into deck YAML."""

from __future__ import annotations

from pathlib import Path

import pytest

from hebrew_cards.anki.collection import FLAG_GREEN, FLAG_NONE, FLAG_RED, RawNote
from hebrew_cards.ids import note_guid
from hebrew_cards.loader import load_all
from hebrew_cards.models import DeckFile, DeckMeta, Entry
from hebrew_cards.review import harvest, index_by_guid

DECKS_DIR = Path(__file__).resolve().parents[2] / "data" / "decks"


def a_deck(*entries: Entry) -> list[tuple[Path, DeckFile]]:
    return [(Path("nouns.yaml"), DeckFile(meta=DeckMeta(name="Nouns"), entries=list(entries)))]


def flagged_note(entry_id: str, hebrew: str, flag: int, deck_stem: str = "nouns") -> RawNote:
    return RawNote(
        nid=1,
        deck="Modern Hebrew::Nouns",
        notetype="MHF Noun",
        fields=(hebrew, "ball", "", "", "", "", ""),
        tags="src::mhf needs-review",
        guid=note_guid(deck_stem, entry_id),
        flag=flag,
    )


def an_entry(**kwargs: object) -> Entry:
    base = dict(id="ball", pos="noun", hebrew="כָּדוּר", english="ball", needs_review=True)
    base.update(kwargs)
    return Entry(**base)  # type: ignore[arg-type]


def test_green_flag_clears_the_review_flag() -> None:
    entry = an_entry()
    entry.review_notes = ["unpointed"]
    decks = a_deck(entry)
    harvest(decks, [flagged_note("ball", "כָּדוּר", FLAG_GREEN)])
    assert entry.needs_review is False
    assert entry.review_notes == []


def test_red_flag_keeps_the_entry_flagged() -> None:
    entry = an_entry(needs_review=False)
    decks = a_deck(entry)
    harvest(decks, [flagged_note("ball", "כָּדוּר", FLAG_RED)])
    assert entry.needs_review is True


def test_unflagged_notes_are_left_alone() -> None:
    """Only an explicit verdict may change the source of truth."""
    entry = an_entry()
    decks = a_deck(entry)
    result = harvest(decks, [flagged_note("ball", "שִׁנּוּי", FLAG_NONE)])
    assert entry.hebrew == "כָּדוּר", "an unflagged edit must not be adopted"
    assert entry.needs_review is True
    assert result.changes == []


def test_an_edit_made_in_anki_is_adopted() -> None:
    entry = an_entry(hebrew="עשה")
    decks = a_deck(entry)
    result = harvest(decks, [flagged_note("ball", "עָשָׂה", FLAG_GREEN)])
    assert entry.hebrew == "עָשָׂה"
    assert result.edits == 1
    assert result.changes[0].edited


def test_a_verb_edit_lands_on_the_lemma() -> None:
    entry = Entry(id="ball", pos="verb", lemma="עשה", english="do", needs_review=True)
    decks = a_deck(entry)
    harvest(decks, [flagged_note("ball", "עָשָׂה", FLAG_GREEN)])
    assert entry.lemma == "עָשָׂה"
    assert entry.hebrew is None


def test_an_adjective_edit_updates_the_ms_form_too() -> None:
    """forms.ms is the citation form; leaving it stale would contradict `hebrew`."""
    entry = Entry(
        id="ball", pos="adjective", hebrew="טוב", english="good",
        forms={"ms": "טוב", "fs": "טוֹבָה"},
    )
    decks = a_deck(entry)
    harvest(decks, [flagged_note("ball", "טוֹב", FLAG_GREEN)])
    assert entry.hebrew == "טוֹב"
    assert entry.forms == {"ms": "טוֹב", "fs": "טוֹבָה"}


def test_an_empty_field_never_wipes_the_hebrew() -> None:
    """A blank field in Anki is far more likely a mistake than an intended deletion."""
    entry = an_entry()
    decks = a_deck(entry)
    harvest(decks, [flagged_note("ball", "   ", FLAG_GREEN)])
    assert entry.hebrew == "כָּדוּר"


def test_a_note_matching_nothing_is_reported_not_ignored() -> None:
    decks = a_deck(an_entry())
    result = harvest(decks, [flagged_note("ball", "כָּדוּר", FLAG_GREEN, deck_stem="verbs-paal")])
    assert result.changes == []
    assert len(result.unmatched) == 1


@pytest.mark.integration
def test_guids_index_the_real_decks_uniquely() -> None:
    """Harvest matches notes to entries by GUID, so collisions would misapply edits."""
    decks = load_all(DECKS_DIR)
    index = index_by_guid(decks)
    total = sum(len(deck.entries) for _, deck in decks)
    assert len(index) == total, "a GUID collision would let one note overwrite another"


@pytest.mark.integration
def test_harvest_against_the_real_deck_data() -> None:
    """Approving a real flagged entry clears it, and nothing else moves."""
    decks = load_all(DECKS_DIR)
    target = None
    for path, deck in decks:
        for entry in deck.entries:
            if entry.needs_review:
                target = (path, entry)
                break
        if target:
            break
    assert target is not None, "expected some flagged entries in the real data"
    path, entry = target

    before = sum(1 for _, d in decks for e in d.entries if e.needs_review)
    note = RawNote(
        nid=1, deck="Modern Hebrew", notetype="MHF Noun",
        fields=(entry.hebrew or entry.lemma or "", entry.english),
        tags="src::mhf", guid=note_guid(path.stem, entry.id), flag=FLAG_GREEN,
    )
    result = harvest(decks, [note])

    assert entry.needs_review is False
    assert result.approved == 1
    after = sum(1 for _, d in decks for e in d.entries if e.needs_review)
    assert after == before - 1, "exactly one entry should have changed"
