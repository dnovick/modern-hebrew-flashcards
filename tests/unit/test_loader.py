"""Tests for deck YAML loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from hebrew_cards.loader import DeckLoadError, load_all, load_deck

VALID = """
meta:
  name: Nouns
entries:
- id: ball
  pos: noun
  hebrew: כָּדוּר
  english: ball
"""


def write(tmp_path: Path, text: str, name: str = "nouns.yaml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_a_valid_deck(tmp_path: Path) -> None:
    deck = load_deck(write(tmp_path, VALID))
    assert deck.meta.name == "Nouns"
    assert deck.entries[0].hebrew == "כָּדוּר"
    assert deck.meta.card_types == ["audio_meaning"]


def test_malformed_yaml_names_the_file(tmp_path: Path) -> None:
    with pytest.raises(DeckLoadError, match="nouns.yaml"):
        load_deck(write(tmp_path, "meta: [unclosed\n"))


def test_non_mapping_top_level_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(DeckLoadError, match="expected a mapping"):
        load_deck(write(tmp_path, "- just\n- a list\n"))


def test_validation_error_names_the_field(tmp_path: Path) -> None:
    """A bad part of speech should stop the build, not silently drop the entry."""
    bad = VALID.replace("pos: noun", "pos: sandwich")
    with pytest.raises(DeckLoadError, match="pos"):
        load_deck(write(tmp_path, bad))


def test_duplicate_ids_are_rejected(tmp_path: Path) -> None:
    """Duplicate ids would collide on GUID and silently lose a note."""
    doubled = VALID + """
- id: ball
  pos: noun
  hebrew: כַּדּוּר
  english: sphere
"""
    with pytest.raises(DeckLoadError, match="duplicate entry id"):
        load_deck(write(tmp_path, doubled))


def test_load_all_is_sorted_and_nonempty(tmp_path: Path) -> None:
    write(tmp_path, VALID, "b.yaml")
    write(tmp_path, VALID, "a.yaml")
    loaded = load_all(tmp_path)
    assert [p.name for p, _ in loaded] == ["a.yaml", "b.yaml"]


def test_load_all_rejects_an_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(DeckLoadError, match="no deck files"):
        load_all(tmp_path)
