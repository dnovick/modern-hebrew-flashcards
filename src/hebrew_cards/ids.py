"""Stable identifiers for decks, note types, and notes.

Every id here is derived from a name or key by hashing, never from a timestamp or
random source. Two builds of the same data therefore produce the same ids, which is
what lets a re-import update notes in place instead of duplicating them.
"""

from __future__ import annotations

import hashlib

# Anki ids are positive integers. Real ones are epoch milliseconds; derived ones only
# need to be stable and collision-free, so the top of the 63-bit range is used to keep
# them clear of anything Anki would mint itself.
_ID_SPACE = 1 << 62


def stable_id(name: str) -> int:
    """A deterministic Anki id for a deck or note type `name`."""
    digest = hashlib.sha1(name.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % _ID_SPACE + _ID_SPACE


def note_guid(deck_slug: str, entry_id: str) -> str:
    """The GUID Anki matches on when importing.

    Derived from the deck and the entry id only — never from translations or other
    mutable content, so editing a gloss updates the note rather than replacing it.
    Changing an entry's `id` orphans its note; see CLAUDE.md.
    """
    key = f"mh::{deck_slug}::{entry_id}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
