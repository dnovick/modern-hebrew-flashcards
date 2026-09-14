"""Cleaning helpers for text pulled out of Anki fields.

The existing collection accumulated HTML entities, stray non-breaking spaces, and
tag strings leaked from Apple Notes' CoreData layer. None of that should survive
into the YAML source of truth.
"""

from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")

# Tags in this collection are polluted with serialized CoreData objects, e.g.
#   "<MCTag: <x-coredata://B0955960-.../MCTag/p5>; data: id: MCTag; (entity: 0x...)"
# Anything containing these markers is machine debris, not a real tag.
_JUNK_TAG_MARKERS = ("MCTag", "x-coredata", "entity:", "<fault>", "0x")


def strip_html(text: str) -> str:
    """Unescape entities and remove tags, turning <br> into a newline."""
    text = _BR_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def clean_tags(raw: str) -> list[str]:
    """Split an Anki tag string, discarding CoreData debris.

    Anki stores tags space-separated. The junk in this collection contains spaces
    of its own, so it cannot be split cleanly — the whole string is inspected for
    debris markers and dropped wholesale when any are present.
    """
    if any(marker in raw for marker in _JUNK_TAG_MARKERS):
        return []
    return [tag for tag in raw.split() if tag]


def slugify(text: str) -> str:
    """Make a short, stable, filename-safe identifier from an English gloss.

    Only the first comma-separated sense is used, so "fire, lay off, dismiss"
    becomes "fire". Identifiers are internal plumbing (they key the note GUID) and
    never appear on a card, so they are exempt from the no-transliteration rule in
    docs/standards/language.md.
    """
    first = text.split(",")[0].strip().lower()
    slug = _SLUG_STRIP_RE.sub("-", first).strip("-")
    return slug or "entry"


def uniquify(slug: str, taken: set[str]) -> str:
    """Return `slug`, suffixed if needed, so it is unique within `taken`."""
    if slug not in taken:
        taken.add(slug)
        return slug
    n = 2
    while f"{slug}-{n}" in taken:
        n += 1
    result = f"{slug}-{n}"
    taken.add(result)
    return result
