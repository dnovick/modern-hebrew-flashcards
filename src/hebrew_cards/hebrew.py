"""Hebrew text utilities: normalization, nikud handling, script detection.

Nothing here ever *adds* or *alters* Hebrew letters. Functions either normalize
Unicode form, remove pointing, or measure properties of a string. Generating or
correcting Hebrew is out of scope by project rule (see CLAUDE.md, hard rule 5).
"""

from __future__ import annotations

import unicodedata

# Hebrew points and marks (nikud, dagesh, sin/shin dots, meteg, and cantillation).
# U+0591–U+05AF are cantillation (te'amim); U+05B0–U+05BD, U+05BF, U+05C1–U+05C2,
# U+05C7 are the vowel points and dots used in Modern Hebrew.
_NIKUD = frozenset(
    [chr(c) for c in range(0x0591, 0x05B0)]          # cantillation
    + [chr(c) for c in range(0x05B0, 0x05BE)]        # vowel points + dagesh
    + ["ֿ", "ׁ", "ׂ", "ׇ"]       # rafe, shin/sin dots, qamats qatan
)

# Hebrew letters proper (alef–tav, including final forms).
_LETTERS = frozenset(chr(c) for c in range(0x05D0, 0x05EB))

# Characters that carry no meaning but routinely leak in from copy-paste.
_JUNK = " ‎‏‪‫‬﻿"


def normalize(text: str) -> str:
    """NFC-normalize and strip junk whitespace/direction marks."""
    text = unicodedata.normalize("NFC", text)
    for ch in _JUNK:
        text = text.replace(ch, " ")
    return " ".join(text.split())


def is_point(ch: str) -> bool:
    """True if `ch` is a Hebrew point or mark rather than a letter."""
    return ch in _NIKUD


def strip_nikud(text: str) -> str:
    """Return `text` with all pointing removed, letters untouched."""
    return "".join(ch for ch in text if ch not in _NIKUD)


def letters(text: str) -> str:
    """Return only the Hebrew letters in `text`."""
    return "".join(ch for ch in text if ch in _LETTERS)


def has_hebrew(text: str) -> bool:
    """True if `text` contains at least one Hebrew letter."""
    return any(ch in _LETTERS for ch in text)


def hebrew_ratio(text: str) -> float:
    """Fraction of non-space characters that are Hebrew letters or points.

    Used to decide which of two Anki fields holds the Hebrew, rather than
    trusting field order — the collection is inconsistent about which side the
    Hebrew sits on.
    """
    meaningful = [ch for ch in text if not ch.isspace()]
    if not meaningful:
        return 0.0
    hebrew = [ch for ch in meaningful if ch in _LETTERS or ch in _NIKUD]
    return len(hebrew) / len(meaningful)


def pointing_ratio(text: str) -> float:
    """Points per Hebrew letter — a rough measure of how fully pointed `text` is.

    A fully pointed Modern Hebrew word lands near or above 0.6; an unpointed one
    is 0.0. This is a heuristic for *flagging* entries for human review, never for
    correcting them.
    """
    letter_count = len(letters(text))
    if letter_count == 0:
        return 0.0
    point_count = sum(1 for ch in text if ch in _NIKUD)
    return point_count / letter_count


# Letters that can act as vowel carriers (matres lectionis) rather than consonants.
_MATRES = frozenset("אהוי")

# Vowel points proper — dagesh (U+05BC) is excluded because it marks gemination or
# a plosive, not a vowel, and a letter carrying only a dagesh is still unvowelled.
_VOWELS = frozenset(chr(c) for c in range(0x05B0, 0x05BC)) | {"ֽ", "ׇ", "ֿ"}


def _letter_clusters(text: str) -> list[tuple[str, str]]:
    """Split `text` into (letter, attached marks) pairs, in order."""
    clusters: list[tuple[str, str]] = []
    for ch in text:
        if ch in _LETTERS:
            clusters.append((ch, ""))
        elif ch in _NIKUD and clusters:
            letter, marks = clusters[-1]
            clusters[-1] = (letter, marks + ch)
    return clusters


def under_pointed(word: str) -> bool:
    """True if `word` has at least one consonant that should carry a vowel but does not.

    A points-per-letter ratio cannot do this job: טוֹב and כָּדוּר are both fully and
    correctly pointed despite carrying few marks, because the vowel rides on a
    following mater lectionis rather than on the consonant itself. Ratios flag those
    as defective and miss real omissions like הפְקִיד (which wants a hiriq under the ה).

    A consonant counts as vowelled when it carries a vowel point of its own, or when
    the next letter is a pointed mater. Word-final letters and non-initial matres are
    exempt — neither takes a vowel in normal pointing.
    """
    # Each word is judged on its own: the final-letter exemption is per word, not
    # per string, so a phrase would otherwise flag every word but the last.
    parts = word.split()
    if len(parts) > 1:
        return any(under_pointed(part) for part in parts)

    clusters = _letter_clusters(word)
    if not clusters:
        return False
    last = len(clusters) - 1
    for i, (letter, marks) in enumerate(clusters):
        if i == last:
            continue
        if i > 0 and letter in _MATRES:
            continue
        if any(m in _VOWELS for m in marks):
            continue
        nxt_letter, nxt_marks = clusters[i + 1]
        if nxt_letter in "וי" and nxt_marks:
            continue
        return True
    return False


def is_pointed(text: str) -> bool:
    """True if `text` carries pointing and none of it is obviously missing."""
    return pointing_ratio(text) > 0 and not under_pointed(text)
