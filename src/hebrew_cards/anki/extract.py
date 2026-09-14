"""Turn raw Anki notes into deck source entries.

Extraction recovers what the old collection actually contains: a Hebrew form, an
English gloss, and whatever the deck name implies about part of speech. It does not
invent linguistic metadata — gender, plurals, roots, and paradigms are absent from
the source and are added later, by enrichment, under human review.

`needs_review` means *something about this extraction looks wrong* — unpointed
Hebrew, an ambiguous part of speech, a parse that did not match its expected shape.
It deliberately does not mean "not yet enriched": flagging every entry for missing
metadata that was never there would drown the signal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .. import hebrew
from ..models import Entry
from ..textclean import clean_tags, slugify, strip_html, uniquify
from .collection import RawNote

# Hebrew in parentheses after a verb is the preposition it governs: נִטְפָּל (אל)
_GOVERNS_RE = re.compile(r"\(([^)]*)\)\s*$")

# The Human Attributes deck stores its answer as
#   "<translit> — <english>\nf. <hebrew feminine> <translit>"
_DASHES = ("—", "–", "־")

# A contiguous run of Hebrew letters and points.
_HEBREW_RUN_RE = re.compile(r"[\u0590-\u05FF]+")


@dataclass(frozen=True)
class DeckRule:
    """How one source deck maps onto a deck file."""

    filename: str
    pos: str
    binyan: str | None = None
    tags: tuple[str, ...] = ()


DECK_RULES: dict[str, DeckRule] = {
    "Modern Hebrew::Nouns": DeckRule("nouns", "noun"),
    "Modern Hebrew::Fruit": DeckRule("fruit", "noun", tags=("topic::fruit",)),
    "Modern Hebrew::Adjectives": DeckRule("adjectives", "adjective"),
    "Modern Hebrew::Human Attributes": DeckRule(
        "human-attributes", "adjective", tags=("topic::human-attributes",)
    ),
    "Modern Hebrew::Adverbs": DeckRule("adverbs", "adverb"),
    "Modern Hebrew::Prepositions": DeckRule("prepositions", "preposition"),
    "Modern Hebrew::Modals": DeckRule("modals", "modal"),
    "Modern Hebrew::Verbs::Paal": DeckRule("verbs-paal", "verb", binyan="paal"),
    "Modern Hebrew::Verbs::Niphal": DeckRule("verbs-niphal", "verb", binyan="niphal"),
    "Modern Hebrew::Verbs::Piel": DeckRule("verbs-piel", "verb", binyan="piel"),
    "Modern Hebrew::Verbs::Hiphil": DeckRule("verbs-hiphil", "verb", binyan="hiphil"),
    "Modern Hebrew::Verbs::Hitpael": DeckRule("verbs-hitpael", "verb", binyan="hitpael"),
    "Modern Hebrew::Verbs::Modal": DeckRule("verbs-modal", "modal"),
    "Modern Hebrew::Verbs::General": DeckRule("verbs-general", "verb"),
}


def split_fields(note: RawNote) -> tuple[str, str]:
    """Return (hebrew_side, english_side) for a two-field note.

    Field *order* is not trusted. Most of the collection is English-first, but the
    Human Attributes deck is Hebrew-first, and both of its fields contain Hebrew.
    Whichever field is denser in Hebrew is the Hebrew one.
    """
    if len(note.fields) != 2:
        raise ValueError(f"note {note.nid}: expected 2 fields, got {len(note.fields)}")
    first, second = note.fields
    if hebrew.hebrew_ratio(first) >= hebrew.hebrew_ratio(second):
        return first, second
    return second, first


def parse_human_attribute(text: str) -> tuple[str, str | None]:
    """Parse the Human Attributes answer format.

    Returns (english, feminine_form). Transliterations are discarded — see
    docs/standards/language.md. Returns an empty english when the shape does not
    match, so the caller can flag it rather than silently keeping garbage.
    """
    lines = text.split("\n")
    english = ""
    for dash in _DASHES:
        if dash in lines[0]:
            english = lines[0].split(dash, 1)[1].strip()
            break
    else:
        # No dash: the whole first line is the gloss, transliteration and all.
        english = lines[0].strip()

    feminine: str | None = None
    for line in lines[1:]:
        # Pull the Hebrew out by codepoint range rather than subtracting Latin —
        # the transliterations carry accented characters (tová, adivá) that a
        # naive a-z filter leaves behind.
        runs = _HEBREW_RUN_RE.findall(line)
        if runs:
            feminine = hebrew.normalize(" ".join(runs))
            break
    return english, feminine


def extract_note(note: RawNote, rule: DeckRule) -> Entry:
    """Build one `Entry` from one raw note."""
    heb_raw, eng_raw = split_fields(note)
    heb = hebrew.normalize(strip_html(heb_raw))
    eng = strip_html(eng_raw)

    feminine: str | None = None
    if rule.filename == "human-attributes":
        eng, feminine = parse_human_attribute(eng)
    else:
        eng = eng.replace("\n", "; ")

    governs: str | None = None
    match = _GOVERNS_RE.search(heb)
    if match and hebrew.has_hebrew(match.group(1)):
        governs = hebrew.normalize(match.group(1))
        heb = hebrew.normalize(heb[: match.start()])

    entry = Entry(
        id="",  # assigned by assign_ids() after deduplication
        pos=rule.pos,  # type: ignore[arg-type]
        english=eng,
        tags=[*rule.tags, *clean_tags(note.tags)],
        source_nid=note.nid,
    )
    if rule.pos == "verb":
        entry.lemma = heb
        entry.binyan = rule.binyan
    else:
        entry.hebrew = heb
    if feminine:
        entry.forms = {"ms": heb, "fs": feminine}
    if governs:
        entry.governs = governs
        entry.flag(f"governs {governs!r}, split out of the Hebrew field — confirm")

    _flag_problems(entry, heb, eng, rule)
    return entry


def _flag_problems(entry: Entry, heb: str, eng: str, rule: DeckRule) -> None:
    """Flag anything about this extraction that looks wrong."""
    if not heb:
        entry.flag("no Hebrew found in the source note")
    elif hebrew.pointing_ratio(heb) == 0.0:
        entry.flag("unpointed")
    elif hebrew.under_pointed(heb):
        entry.flag("a consonant appears to be missing its vowel point")
    if not eng:
        entry.flag("no English gloss recovered")
    if heb and hebrew.is_point(heb[0]):
        entry.flag("a pointing mark precedes the first letter — the nikud is misplaced")
    if rule.filename == "human-attributes" and not entry.forms:
        entry.flag("expected a feminine form in the answer field, found none")
    # Verbs::General is not exclusively verbs — it holds adverbs such as
    # תֵכֶף "instantaneously" and בְּפֵרוּשׁ "clearly". An -ly gloss is a weak signal, so
    # the part of speech is left alone and only flagged.
    if rule.filename == "verbs-general" and eng.split(",")[0].strip().endswith("ly"):
        entry.flag("gloss looks adverbial; this source deck mixes parts of speech")


def _key(entry: Entry) -> tuple[str, str]:
    """Identity for deduplication: the Hebrew form plus the English gloss."""
    return ((entry.hebrew or entry.lemma or ""), entry.english.strip().lower())


def dedupe(entries: list[Entry]) -> tuple[list[Entry], int]:
    """Drop exact duplicates; flag same-Hebrew-different-gloss collisions.

    The collection was imported more than once at some point — the Fruit deck holds
    six fruits stored three times each. Notes identical in both Hebrew and gloss are
    mechanical noise and are collapsed to one. Notes sharing Hebrew but glossing it
    differently ("disturb" vs "interrupt, interfere") are a content judgement, so
    both survive and are flagged for the owner to merge.
    """
    kept: list[Entry] = []
    seen: dict[tuple[str, str], Entry] = {}
    dropped = 0
    for entry in entries:
        key = _key(entry)
        if key in seen:
            dropped += 1
            continue
        seen[key] = entry
        kept.append(entry)

    by_hebrew: dict[str, list[Entry]] = {}
    for entry in kept:
        form = entry.hebrew or entry.lemma or ""
        if form:
            by_hebrew.setdefault(form, []).append(entry)
    for form, group in by_hebrew.items():
        if len(group) > 1:
            glosses = " / ".join(sorted(e.english for e in group))
            for entry in group:
                entry.flag(
                    f"{form} also appears in this deck with a different gloss "
                    f"({glosses}) — merge or disambiguate"
                )

    return kept, dropped


def assign_ids(entries: list[Entry]) -> None:
    """Give each entry a unique, stable id derived from its English gloss."""
    taken: set[str] = set()
    for entry in entries:
        entry.id = uniquify(slugify(entry.english), taken)
