"""Pure-logic tests for Hebrew text handling. No I/O."""

from __future__ import annotations

import pytest

from hebrew_cards import hebrew


@pytest.mark.parametrize(
    "word",
    [
        "כָּדוּר",      # vowel on the consonant, then a pointed mater
        "טוֹב",        # holam rides the vav — few marks, fully correct
        "גוּר",
        "תוּת",
        "אֵיכוּת",
        "הוֹאִיל",
        "טֵירוּף",
        "רִיהוּט",
        "פִטֵּר",
        "הִפְקִיד",
        "הִגְבִּיל",
        "מְשַׂגְשֵׂג",
    ],
)
def test_correctly_pointed_words_are_not_flagged(word: str) -> None:
    """Words using matres lectionis carry few marks but are not defective.

    This is the case a points-per-letter ratio gets wrong: טוֹב scores 0.33 and
    looks half-pointed, yet nothing is missing from it.
    """
    assert not hebrew.under_pointed(word)


@pytest.mark.parametrize(
    "word",
    [
        "הפְקִיד",      # the ה wants a hiriq
        "עשה",         # no pointing at all
        "נמנע",
        "חסר מושג",    # unpointed phrase
    ],
)
def test_missing_vowels_are_flagged(word: str) -> None:
    assert hebrew.under_pointed(word)


def test_each_word_in_a_phrase_is_judged_separately() -> None:
    """The final-letter exemption is per word; a pointed phrase must stay clean."""
    assert not hebrew.under_pointed("נִטְפָּל אֶל")


def test_strip_nikud_leaves_letters_untouched() -> None:
    assert hebrew.strip_nikud("כָּדוּר") == "כדור"
    assert hebrew.strip_nikud("עשה") == "עשה"


def test_hebrew_ratio_picks_the_denser_field() -> None:
    """Used to decide which Anki field holds the Hebrew, since order varies."""
    hebrew_side = "טוֹב"
    english_side = "tov — good f. טוֹבָה tová"
    assert hebrew.hebrew_ratio(hebrew_side) > hebrew.hebrew_ratio(english_side)


def test_normalize_strips_direction_marks_and_nbsp() -> None:
    assert hebrew.normalize("\xa0 \xa0פּוֹצֵץ") == "פּוֹצֵץ"


def test_pointing_ratio_is_zero_for_unpointed_text() -> None:
    assert hebrew.pointing_ratio("עשה") == 0.0
    assert hebrew.pointing_ratio("") == 0.0
