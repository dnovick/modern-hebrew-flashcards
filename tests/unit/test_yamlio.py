"""Tests for deck YAML serialization. No I/O."""

from __future__ import annotations

import yaml

from hebrew_cards.models import DeckFile, DeckMeta, Entry
from hebrew_cards.yamlio import dump_deck


def a_deck(entry: Entry) -> DeckFile:
    return DeckFile(meta=DeckMeta(name="Nouns", source_deck="Modern Hebrew::Nouns"), entries=[entry])


def test_absent_fields_are_omitted_not_written_as_null() -> None:
    """A hand-editing human should see only fields that carry information."""
    text = dump_deck(a_deck(Entry(id="ball", pos="noun", english="ball", hebrew="כָּדוּר")))
    assert "gender" not in text
    assert "null" not in text
    assert "needs_review" not in text


def test_hebrew_is_written_unescaped() -> None:
    text = dump_deck(a_deck(Entry(id="ball", pos="noun", english="ball", hebrew="כָּדוּר")))
    assert "כָּדוּר" in text
    assert "\\u05" not in text


def test_round_trips_through_yaml() -> None:
    entry = Entry(
        id="good",
        pos="adjective",
        english="good",
        hebrew="טוֹב",
        forms={"ms": "טוֹב", "fs": "טוֹבָה"},
        tags=["topic::human-attributes"],
        needs_review=True,
        review_notes=["check the feminine"],
        source_nid=42,
    )
    loaded = yaml.safe_load(dump_deck(a_deck(entry)))
    assert loaded["meta"]["name"] == "Nouns"
    assert loaded["entries"][0] == {
        "id": "good",
        "pos": "adjective",
        "hebrew": "טוֹב",
        "english": "good",
        "forms": {"ms": "טוֹב", "fs": "טוֹבָה"},
        "tags": ["topic::human-attributes"],
        "needs_review": True,
        "review_notes": ["check the feminine"],
        "source_nid": 42,
    }


def test_identifying_fields_come_before_authoring_metadata() -> None:
    """Field order is fixed so a deck file scans quickly."""
    text = dump_deck(
        a_deck(Entry(id="x", pos="noun", english="x", hebrew="א", needs_review=True,
                     review_notes=["why"], source_nid=1))
    )
    assert text.index("id:") < text.index("english:") < text.index("needs_review:")
