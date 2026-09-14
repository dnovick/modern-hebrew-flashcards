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

    Asserts invariants rather than a note count: the collection is live user data that
    legitimately changes, and an exact count would fail every time the owner adds a
    card. What must always hold is that only the legacy tree is read, that generated
    decks are never read back, and that a known word extracts correctly.
    """
    if not DEFAULT_COLLECTION.exists():
        pytest.skip("no local Anki collection")

    from hebrew_cards.anki import collection as col

    copy = col.copy_collection(tmp_path / "collection.anki2")
    notes = col.read_notes(copy)

    assert notes, "expected some Modern Hebrew notes"
    # Nothing from BBH, BBG, Biblical Hebrew, or Psalm 119.
    assert all(col.in_scope(n.deck) for n in notes), "out-of-scope deck leaked"
    # And nothing from this pipeline's own output, which shares the name prefix once
    # a generated package has been imported into the same collection.
    assert not any("(rebuild)" in n.deck for n in notes), "generated decks read back as source"

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

    assert total > 0
    assert ball is not None, "the noun deck should yield an entry with id 'ball'"
    assert ball.hebrew == "כָּדוּר"     # nbsp stripped from the English side
    assert ball.english == "ball"
    assert ball.pos == "noun"
    assert not ball.needs_review


def test_only_the_modern_hebrew_tree_is_in_scope() -> None:
    from hebrew_cards.anki.collection import in_scope

    assert in_scope("Modern Hebrew")
    assert in_scope("Modern Hebrew::Nouns")
    assert in_scope("Modern Hebrew::Verbs::Paal")
    assert not in_scope("BBH::Vocabulary::Chapter 26")
    assert not in_scope("Psalm 119::01 Alef — Vocabulary")
    assert not in_scope("Biblical Hebrew::Root Deck")


def test_generated_notes_are_never_read_back_as_source() -> None:
    """Generated decks now carry the same names the source decks did.

    The staging root was retired when the owner deleted the legacy tree, so deck name
    can no longer separate source from output. These markers ride on the note itself
    and survive any rename or move; without them, a re-extraction would treat derived
    data as source and double every deck.
    """
    from hebrew_cards.anki.collection import is_generated

    assert is_generated("MHF Noun", "pos::noun src::mhf")
    assert is_generated("MHF Verb", "")
    assert is_generated("Basic", "src::mhf other")      # tag alone is enough
    assert not is_generated("Basic_2_fields", "adjectives character positive")
    assert not is_generated("Basic", "")
    # A tag that merely contains the marker as a substring is not the marker.
    assert not is_generated("Basic", "src::mhfx")


@pytest.mark.integration
def test_generated_notes_are_found_outside_the_modern_hebrew_tree(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Harvest must see generated notes wherever they live.

    During migration they sit under a staging root ("Modern Hebrew (rebuild)"), which
    the source-side scope check deliberately excludes. Applying that check to the
    generated side too made harvest report zero notes and silently do nothing.
    """
    if not DEFAULT_COLLECTION.exists():
        pytest.skip("no local Anki collection")

    from hebrew_cards.anki import collection as col

    copy = col.copy_collection(tmp_path / "collection.anki2")
    generated = col.read_notes(copy, generated=True)
    source = col.read_notes(copy, generated=False)

    # Whatever the deck layout, the two sides never overlap.
    assert not ({n.nid for n in generated} & {n.nid for n in source})
    # Source notes are confined to the Modern Hebrew tree; generated ones are not.
    assert all(col.in_scope(n.deck) for n in source)
    assert all(col.is_generated(n.notetype, n.tags) for n in generated)
