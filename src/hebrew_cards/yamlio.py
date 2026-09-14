"""Serialize deck files to YAML.

Field order is fixed and meaningful — the identifying fields come first so a deck
file can be scanned quickly, and authoring metadata sinks to the bottom. Empty and
absent values are omitted entirely rather than written as nulls, so a hand-editing
human sees only fields that carry information.
"""

from __future__ import annotations

from typing import Any

import yaml

from .models import DeckFile, Entry

_FIELD_ORDER = (
    "id",
    "pos",
    "hebrew",
    "lemma",
    "english",
    "gender",
    "plural",
    "forms",
    "root",
    "binyan",
    "gizra",
    "infinitive",
    "drill",
    "governs",
    "audio",
    "tags",
    "needs_review",
    "review_notes",
    "source_nid",
)


def _entry_to_dict(entry: Entry) -> dict[str, Any]:
    raw = entry.model_dump()
    out: dict[str, Any] = {}
    for key in _FIELD_ORDER:
        value = raw.get(key)
        if value in (None, [], {}, False):
            continue
        out[key] = value
    return out


def dump_deck(deck: DeckFile) -> str:
    """Render a deck file as YAML text."""
    meta = {k: v for k, v in deck.meta.model_dump().items() if v not in (None, [], {})}
    payload = {"meta": meta, "entries": [_entry_to_dict(e) for e in deck.entries]}
    return yaml.dump(
        payload,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=200,
    )
