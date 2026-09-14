"""Pure-logic tests for Anki field cleaning. No I/O."""

from __future__ import annotations

from hebrew_cards.textclean import clean_tags, slugify, strip_html, uniquify

CORE_DATA_JUNK = (
    " (entity: 0x8c134c517858df69 <fault>) <MCTag: "
    "<x-coredata://B0955960-564F-445E-A7F1-E2D37C7BAADA/MCTag/p5>; data: id: MCTag; "
)


def test_strip_html_turns_br_into_a_line_break() -> None:
    assert strip_html("tov — good<br><i>f.</i> טוֹבָה") == "tov — good\nf. טוֹבָה"


def test_strip_html_unescapes_entities_and_nbsp() -> None:
    assert strip_html("&nbsp;ball") == "ball"


def test_clean_tags_discards_coredata_debris() -> None:
    """These leaked in from Apple Notes and are not real tags."""
    assert clean_tags(CORE_DATA_JUNK) == []


def test_clean_tags_keeps_real_tags() -> None:
    assert clean_tags(" adjectives character hebrew positive ") == [
        "adjectives",
        "character",
        "hebrew",
        "positive",
    ]


def test_slugify_uses_only_the_first_sense() -> None:
    assert slugify("fire, lay off, dismiss") == "fire"
    assert slugify("for, for the sake of, on behalf of") == "for"


def test_slugify_never_returns_empty() -> None:
    assert slugify("...") == "entry"


def test_uniquify_suffixes_collisions() -> None:
    taken: set[str] = set()
    assert uniquify("save", taken) == "save"
    assert uniquify("save", taken) == "save-2"
    assert uniquify("save", taken) == "save-3"
