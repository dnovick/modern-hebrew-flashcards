"""Tests for derived Anki identifiers. No I/O."""

from __future__ import annotations

from hebrew_cards.ids import note_guid, stable_id


def test_stable_id_is_deterministic() -> None:
    """Rebuilds must reuse ids, or every import creates a second note type."""
    assert stable_id("MHF Noun") == stable_id("MHF Noun")


def test_stable_id_differs_by_name() -> None:
    assert stable_id("MHF Noun") != stable_id("MHF Verb")


def test_stable_id_is_a_positive_anki_id() -> None:
    assert 0 < stable_id("MHF Noun") < (1 << 63)


def test_note_guid_is_deterministic() -> None:
    assert note_guid("nouns", "ball") == note_guid("nouns", "ball")


def test_note_guid_is_scoped_by_deck() -> None:
    """The same word in two decks is two notes, not a collision."""
    assert note_guid("nouns", "ball") != note_guid("fruit", "ball")


def test_note_guid_differs_by_entry() -> None:
    assert note_guid("nouns", "ball") != note_guid("nouns", "abundance")
