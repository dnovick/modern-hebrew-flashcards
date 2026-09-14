"""Tests for the command-line entry points.

The library modules were well covered while the scripts that drive them were not,
which is how a coverage floor slipped: most new code in a feature lands in its CLI.
These load each script by path and call main() directly, so the work is measured
rather than hidden in a subprocess.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"

DECK_YAML = """
meta:
  name: Nouns
entries:
- id: ball
  pos: noun
  hebrew: כָּדוּר
  english: ball
- id: promise
  pos: verb
  lemma: הִבְטִיחַ
  english: promise
  binyan: hiphil
"""


def load_script(name: str) -> ModuleType:
    """Import a script by path — scripts/ is not a package."""
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"_script_{path.stem}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def decks_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "decks"
    directory.mkdir()
    (directory / "nouns.yaml").write_text(DECK_YAML, encoding="utf-8")
    return directory


def run(module: ModuleType, argv: list[str], monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(sys, "argv", ["script", *argv])
    result: int = module.main()
    return result


def test_build_decks_writes_a_package(
    decks_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build = load_script("build_decks.py")
    out = tmp_path / "out.apkg"
    assert run(build, ["--decks", str(decks_dir), "--out", str(out)], monkeypatch) == 0
    assert out.exists() and out.stat().st_size > 0


def test_build_decks_honours_the_deck_root(
    decks_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    build = load_script("build_decks.py")
    out = tmp_path / "out.apkg"
    run(build, ["--decks", str(decks_dir), "--out", str(out), "--deck-root", "Test Root"], monkeypatch)
    assert "Test Root" in capsys.readouterr().out


def test_build_decks_reports_a_bad_deck_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A malformed deck must fail the build loudly, not produce a deck missing cards."""
    bad = tmp_path / "decks"
    bad.mkdir()
    (bad / "nouns.yaml").write_text("meta: [unclosed\n", encoding="utf-8")
    build = load_script("build_decks.py")
    assert run(build, ["--decks", str(bad), "--out", str(tmp_path / "o.apkg")], monkeypatch) == 1
    assert "ERROR" in capsys.readouterr().err


def test_build_decks_reports_an_empty_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    build = load_script("build_decks.py")
    assert run(build, ["--decks", str(empty), "--out", str(tmp_path / "o.apkg")], monkeypatch) == 1


def test_extract_refuses_to_overwrite_existing_decks(
    decks_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Extraction is a one-time migration; a stray re-run would revert hand edits."""
    extract = load_script("extract_collection.py")
    from hebrew_cards.anki.collection import DEFAULT_COLLECTION

    if not DEFAULT_COLLECTION.exists():
        pytest.skip("no local Anki collection")
    assert run(extract, ["--out", str(decks_dir)], monkeypatch) == 1
    assert "already contains" in capsys.readouterr().err
