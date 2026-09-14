"""Tests for extracting deck entries from Anki notes.

The behavioral test at the bottom runs the real extractor against the owner's real
collection, per docs/policies — a mock would not have caught the field-order and
duplicate-import problems this code exists to handle. It is marked `integration`
because that collection is local user data that CI never has.
"""

from __future__ import annotations

import pytest

from hebrew_cards.anki.collection import DEFAULT_COLLECTION, RawNote
from hebrew_cards.anki.extract import (
    DECK_RULES,
    assign_ids,
    dedupe,
    extract_note,
    parse_human_attribute,
    split_fields,
)

NOUN_RULE = DECK_RULES["Modern Hebrew::Nouns"]
HUMAN_RULE = DECK_RULES["Modern Hebrew::Human Attributes"]
VERB_RULE = DECK_RULES["Modern Hebrew::Verbs::Paal"]


def note(*fields: str, deck: str = "Modern Hebrew::Nouns", tags: str = "") -> RawNote:
    return RawNote(nid=1, deck=deck, notetype="Basic", fields=tuple(fields), tags=tags)


def test_split_fields_ignores_field_order() -> None:
    """Most of the collection is English-first; Human Attributes is Hebrew-first."""
    assert split_fields(note("ball", "כָּדוּר")) == ("כָּדוּר", "ball")
    assert split_fields(note("כָּדוּר", "ball")) == ("כָּדוּר", "ball")


def test_split_fields_when_both_sides_contain_hebrew() -> None:
    """The answer side carries the feminine form, so density decides, not presence."""
    hebrew_side, english_side = split_fields(
        note("טוֹב", "tov — good<br><i>f.</i> טוֹבָה <i>tová</i>")
    )
    assert hebrew_side == "טוֹב"
    assert english_side.startswith("tov")


def test_split_fields_rejects_wrong_arity() -> None:
    with pytest.raises(ValueError, match="expected 2 fields"):
        split_fields(note("one"))


def test_parse_human_attribute_drops_transliteration() -> None:
    """Transliteration is forbidden by docs/standards/language.md."""
    english, feminine = parse_human_attribute("tov — good\nf. טוֹבָה tová")
    assert english == "good"
    assert feminine == "טוֹבָה"


def test_parse_human_attribute_survives_an_unexpected_shape() -> None:
    english, feminine = parse_human_attribute("plain gloss only")
    assert english == "plain gloss only"
    assert feminine is None


def test_extract_flags_unpointed_hebrew() -> None:
    entry = extract_note(note("do, make", "עשה"), VERB_RULE)
    assert entry.needs_review
    assert "unpointed" in entry.review_notes


def test_extract_flags_misplaced_leading_point() -> None:
    """apple was stored as ַתַפּוּח — a patach before the first letter."""
    entry = extract_note(note("apple", "ַתַפּוּח"), NOUN_RULE)
    assert entry.needs_review
    assert any("precedes the first letter" in n for n in entry.review_notes)


def test_extract_splits_out_a_governed_preposition() -> None:
    entry = extract_note(note("pick (on someone)", "נִטְפָּל (אל)"), VERB_RULE)
    assert entry.lemma == "נִטְפָּל"
    assert entry.governs == "אל"
    assert entry.needs_review


def test_extract_discards_coredata_tag_junk() -> None:
    entry = extract_note(note("ball", "כָּדוּר", tags="<MCTag: data: id: MCTag;"), NOUN_RULE)
    assert entry.tags == []


def test_verbs_store_the_lemma_not_the_hebrew_field() -> None:
    entry = extract_note(note("pluck", "קָטַף"), VERB_RULE)
    assert entry.lemma == "קָטַף"
    assert entry.hebrew is None
    assert entry.binyan == "paal"


def test_human_attributes_capture_the_feminine_form() -> None:
    entry = extract_note(
        note("טוֹב", "tov — good<br><i>f.</i> טוֹבָה <i>tová</i>"), HUMAN_RULE
    )
    assert entry.english == "good"
    assert entry.forms == {"ms": "טוֹב", "fs": "טוֹבָה"}


def test_dedupe_collapses_identical_notes() -> None:
    """The Fruit deck holds six fruits imported three times each."""
    notes = [note("apple", "תַּפּוּחַ") for _ in range(3)]
    entries = [extract_note(n, NOUN_RULE) for n in notes]
    kept, dropped = dedupe(entries)
    assert len(kept) == 1
    assert dropped == 2


def test_dedupe_keeps_same_hebrew_with_different_glosses_and_flags_them() -> None:
    """Merging "disturb" and "interrupt" is a content judgement, not a cleanup."""
    entries = [
        extract_note(note("disturb", "הִפְרִיע"), VERB_RULE),
        extract_note(note("interrupt, interfere", "הִפְרִיע"), VERB_RULE),
    ]
    kept, dropped = dedupe(entries)
    assert len(kept) == 2
    assert dropped == 0
    assert all(e.needs_review for e in kept)
    assert all(any("different gloss" in n for n in e.review_notes) for e in kept)


def test_assign_ids_is_unique_within_a_deck() -> None:
    entries = [
        extract_note(note("save (money)", "חָסַךְ"), VERB_RULE),
        extract_note(note("save (e.g. money)", "חָסַךְ"), VERB_RULE),
    ]
    assign_ids(entries)
    assert [e.id for e in entries] == ["save-money", "save-e-g-money"]


@pytest.mark.integration
def test_extraction_against_the_real_collection(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Behavioral test: run the real extractor over the real collection.

    Asserts known-correct facts established by inspecting the collection directly:
    457 in-scope notes collapse to 400 entries, nothing outside Modern Hebrew is
    ever read, and a specific known word comes out with the right fields.
    """
    if not DEFAULT_COLLECTION.exists():
        pytest.skip("no local Anki collection")

    from hebrew_cards.anki import collection as col

    copy = col.copy_collection(tmp_path / "collection.anki2")
    notes = col.read_notes(copy)

    assert len(notes) == 457
    assert all(n.deck.startswith("Modern Hebrew") for n in notes), "out-of-scope deck leaked"

    total = 0
    ball = None
    for deck_name, rule in DECK_RULES.items():
        deck_notes = [n for n in notes if n.deck == deck_name]
        entries = [extract_note(n, rule) for n in deck_notes]
        entries, _ = dedupe(entries)
        assign_ids(entries)
        total += len(entries)
        for entry in entries:
            if entry.id == "ball":
                ball = entry

    assert total == 400, "expected 457 source notes to collapse to 400 unique entries"

    assert ball is not None, "the noun deck should yield an entry with id 'ball'"
    assert ball.hebrew == "כָּדוּר"     # nbsp stripped from the English side
    assert ball.english == "ball"
    assert ball.pos == "noun"
    assert not ball.needs_review
