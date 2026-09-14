"""Tests for assembling decks into an Anki package.

The behavioral test at the bottom builds a real .apkg from the real deck data,
opens it, and asserts on what Anki would actually import — the only way to catch a
template that generates no cards or a field mapped to the wrong slot.
"""

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from hebrew_cards.build import PROVENANCE_TAG, build_note, build_package, _field_values, _tags
from hebrew_cards.loader import load_all
from hebrew_cards.models import Entry
from hebrew_cards.notetypes import model_for

DECKS_DIR = Path(__file__).resolve().parents[2] / "data" / "decks"


def noun() -> Entry:
    return Entry(id="ball", pos="noun", hebrew="כָּדוּר", english="ball", gender="m")


def verb() -> Entry:
    return Entry(id="pluck", pos="verb", lemma="קָטַף", english="pluck", binyan="paal")


def test_verb_fields_use_lemma_not_hebrew() -> None:
    values = _field_values(verb())
    assert values["Lemma"] == "קָטַף"
    assert "Hebrew" not in values


def test_adjective_fields_fall_back_to_the_ms_form() -> None:
    entry = Entry(id="good", pos="adjective", english="good", forms={"ms": "טוֹב", "fs": "טוֹבָה"})
    values = _field_values(entry)
    assert values["Hebrew"] == "טוֹב"
    assert values["FormFS"] == "טוֹבָה"


def test_audio_field_is_present_but_empty_until_the_audio_milestone() -> None:
    assert _field_values(noun())["Audio"] == ""


def test_every_note_carries_the_provenance_tag() -> None:
    """src::mhf is what distinguishes generated notes from the legacy ones."""
    assert PROVENANCE_TAG in _tags(noun())


def test_tags_mirror_linguistic_fields() -> None:
    assert "pos::verb" in _tags(verb())
    assert "binyan::paal" in _tags(verb())
    assert "gender::m" in _tags(noun())


def test_flagged_entries_are_findable_in_anki() -> None:
    entry = noun()
    entry.flag("unpointed")
    assert "needs-review" in _tags(entry)


def test_tags_never_contain_spaces() -> None:
    """Anki splits tags on whitespace, so a spaced tag silently becomes two."""
    entry = noun()
    entry.tags = ["topic::human attributes"]
    assert all(" " not in tag for tag in _tags(entry))


def test_fields_are_ordered_to_match_the_note_type() -> None:
    """A mis-ordered list would put the gloss in the Gender slot."""
    note = build_note(noun(), "nouns")
    names = [f["name"] for f in model_for("noun").fields]
    assert note.fields[names.index("Hebrew")] == "כָּדוּר"
    assert note.fields[names.index("English")] == "ball"
    assert note.fields[names.index("Gender")] == "m"


def test_unknown_part_of_speech_is_an_error() -> None:
    with pytest.raises(ValueError, match="no note type"):
        model_for("sandwich")


def _open_package(path: Path, workdir: Path) -> sqlite3.Connection:
    with zipfile.ZipFile(path) as zf:
        zf.extractall(workdir)
    name = "collection.anki21" if (workdir / "collection.anki21").exists() else "collection.anki2"
    return sqlite3.connect(workdir / name)


@pytest.mark.integration
def test_building_the_real_decks(tmp_path: Path) -> None:
    """Behavioral test: build every real deck and inspect the package Anki would read."""
    out = tmp_path / "out.apkg"
    stats = build_package(load_all(DECKS_DIR), out)
    assert stats.notes == 400
    assert stats.decks == 14

    conn = _open_package(out, tmp_path / "unpacked")
    models_json, decks_json = conn.execute("select models, decks from col").fetchone()
    models = json.loads(models_json)
    decks = json.loads(decks_json)

    # Every generated note type is MHF-prefixed, so it cannot be confused with the
    # legacy Basic/Basic_2_fields notes during migration.
    assert all(m["name"].startswith("MHF ") for m in models.values())

    # Builds land under the rebuild root, never in the live Modern Hebrew tree.
    generated = [d["name"] for d in decks.values() if d["name"] != "Default"]
    assert generated, "no decks were written"
    assert all(name.startswith("Modern Hebrew (rebuild)::") for name in generated)

    assert conn.execute("select count(*) from notes").fetchone()[0] == 400
    # One card per note: audio → meaning, no reverse card.
    assert conn.execute("select count(*) from cards").fetchone()[0] == 400
    # The CoreData debris in the source collection must not survive.
    assert conn.execute("select count(*) from notes where tags like '%MCTag%'").fetchone()[0] == 0
    assert conn.execute(
        f"select count(*) from notes where tags not like '%{PROVENANCE_TAG}%'"
    ).fetchone()[0] == 0
    conn.close()


@pytest.mark.integration
def test_rebuilding_produces_identical_guids(tmp_path: Path) -> None:
    """A rebuild must update notes in place, not duplicate them on re-import."""
    decks = load_all(DECKS_DIR)
    guids = []
    for run in ("first", "second"):
        out = tmp_path / f"{run}.apkg"
        build_package(decks, out)
        conn = _open_package(out, tmp_path / run)
        guids.append(sorted(row[0] for row in conn.execute("select guid from notes")))
        conn.close()
    assert guids[0] == guids[1]
    assert len(set(guids[0])) == 400, "GUIDs must be unique across all decks"
