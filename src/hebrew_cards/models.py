"""Schema for deck source data.

One `Entry` model covers every part of speech rather than a model per POS: the
extractor produces a single stream of heterogeneous entries, and per-POS required
fields (a noun's gender, for instance) are enforced at validation time rather than
by the type. See docs/standards/data-model.md for the authoring-facing schema.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PartOfSpeech = Literal[
    "noun", "verb", "adjective", "adverb", "preposition", "modal", "unknown"
]

Gender = Literal["m", "f"]

BINYANIM = ("paal", "niphal", "piel", "pual", "hiphil", "hophal", "hitpael")


class Entry(BaseModel):
    """One lexeme. Becomes one Anki note (plus form notes, for verbs)."""

    id: str
    pos: PartOfSpeech
    english: str

    # Citation form. Nouns/adjectives/particles use `hebrew`; verbs use `lemma`
    # (3ms past), so exactly one of the two is populated.
    hebrew: str | None = None
    lemma: str | None = None

    # Noun
    gender: Gender | None = None
    plural: str | None = None

    # Adjective — ms / fs / mp / fp
    forms: dict[str, str] | None = None

    # Verb
    root: str | None = None
    binyan: str | None = None
    gizra: str | None = None
    infinitive: str | None = None
    drill: list[str] | None = None

    # A preposition the lexeme governs, e.g. נִטְפָּל (אל)
    governs: str | None = None

    tags: list[str] = Field(default_factory=list)

    # Authoring metadata. Stays in YAML; only `needs_review` reaches Anki, as a tag.
    needs_review: bool = False
    review_notes: list[str] = Field(default_factory=list)
    source_nid: int | None = None

    def flag(self, reason: str) -> None:
        """Mark this entry for human review, recording why."""
        self.needs_review = True
        if reason not in self.review_notes:
            self.review_notes.append(reason)


class DeckMeta(BaseModel):
    """Deck-level configuration."""

    name: str
    card_types: list[str] = Field(default_factory=lambda: ["audio_meaning"])
    source_deck: str | None = None
    notes: list[str] = Field(default_factory=list)


class DeckFile(BaseModel):
    """One `data/decks/*.yaml` file."""

    meta: DeckMeta
    entries: list[Entry]
