"""Tests for harvesting review decisions from Anki back into deck YAML."""

from __future__ import annotations

from pathlib import Path

import pytest

from hebrew_cards.anki.collection import FLAG_GREEN, FLAG_NONE, FLAG_RED, RawNote
from hebrew_cards.ids import note_guid
from hebrew_cards.loader import load_all
from hebrew_cards.models import DeckFile, DeckMeta, Entry
from hebrew_cards.review import harvest, index_by_guid

DECKS_DIR = Path(__file__).resolve().parents[2] / "data" / "decks"


def a_deck(*entries: Entry) -> list[tuple[Path, DeckFile]]:
    return [(Path("nouns.yaml"), DeckFile(meta=DeckMeta(name="Nouns"), entries=list(entries)))]


def flagged_note(entry_id: str, hebrew: str, flag: int, deck_stem: str = "nouns") -> RawNote:
    return RawNote(
        nid=1,
        deck="Modern Hebrew::Nouns",
        notetype="MHF Noun",
        fields=(hebrew, "ball", "", "", "", "", ""),
        tags="src::mhf needs-review",
        guid=note_guid(deck_stem, entry_id),
        flag=flag,
    )


def an_entry(**kwargs: object) -> Entry:
    base = dict(id="ball", pos="noun", hebrew="כָּדוּר", english="ball", needs_review=True)
    base.update(kwargs)
    return Entry(**base)  # type: ignore[arg-type]


def test_green_flag_clears_the_review_flag() -> None:
    entry = an_entry()
    entry.review_notes = ["unpointed"]
    decks = a_deck(entry)
    harvest(decks, [flagged_note("ball", "כָּדוּר", FLAG_GREEN)])
    assert entry.needs_review is False
    assert entry.review_notes == []


def test_red_flag_keeps_the_entry_flagged() -> None:
    entry = an_entry(needs_review=False)
    decks = a_deck(entry)
    harvest(decks, [flagged_note("ball", "כָּדוּר", FLAG_RED)])
    assert entry.needs_review is True


def test_unflagged_notes_are_left_alone() -> None:
    """Only an explicit verdict may change the source of truth."""
    entry = an_entry()
    decks = a_deck(entry)
    result = harvest(decks, [flagged_note("ball", "שִׁנּוּי", FLAG_NONE)])
    assert entry.hebrew == "כָּדוּר", "an unflagged edit must not be adopted"
    assert entry.needs_review is True
    assert result.changes == []


def test_an_edit_made_in_anki_is_adopted() -> None:
    entry = an_entry(hebrew="עשה")
    decks = a_deck(entry)
    result = harvest(decks, [flagged_note("ball", "עָשָׂה", FLAG_GREEN)])
    assert entry.hebrew == "עָשָׂה"
    assert result.edits == 1
    assert result.changes[0].edited


def test_a_verb_edit_lands_on_the_lemma() -> None:
    entry = Entry(id="ball", pos="verb", lemma="עשה", english="do", needs_review=True)
    decks = a_deck(entry)
    harvest(decks, [flagged_note("ball", "עָשָׂה", FLAG_GREEN)])
    assert entry.lemma == "עָשָׂה"
    assert entry.hebrew is None


def test_an_adjective_edit_updates_the_ms_form_too() -> None:
    """forms.ms is the citation form; leaving it stale would contradict `hebrew`."""
    entry = Entry(
        id="ball", pos="adjective", hebrew="טוב", english="good",
        forms={"ms": "טוב", "fs": "טוֹבָה"},
    )
    decks = a_deck(entry)
    harvest(decks, [flagged_note("ball", "טוֹב", FLAG_GREEN)])
    assert entry.hebrew == "טוֹב"
    assert entry.forms == {"ms": "טוֹב", "fs": "טוֹבָה"}


def test_an_adjective_with_only_forms_is_not_falsely_stale() -> None:
    """forms["ms"] is the citation form for an entry with no separate `hebrew` key.

    Regression test: adjectives.yaml switched to this forms-only convention once
    every entry had a full paradigm (see the agreement-forms enrichment), and
    _citation() initially only checked `hebrew`/`lemma` — every such entry read as
    an empty citation, which find_stale mistook for the collection being behind.
    """
    from hebrew_cards.review import find_stale

    entry = Entry(
        id="ball", pos="adjective", english="good",
        forms={"ms": "טוֹב", "fs": "טוֹבָה", "mp": "טוֹבִים", "fp": "טוֹבוֹת"},
    )
    decks = a_deck(entry)
    note = flagged_note("ball", "טוֹב", FLAG_NONE)
    note = RawNote(**{**note.__dict__, "fields": ("טוֹב", "good", "", "", "", "", "")})
    assert find_stale(decks, [note]) == []


def test_an_edit_on_a_forms_only_adjective_updates_ms_not_hebrew() -> None:
    """Harvesting an edit must not resurrect a `hebrew` key the convention dropped."""
    entry = Entry(
        id="ball", pos="adjective", english="good",
        forms={"ms": "טוב", "fs": "טוֹבָה", "mp": "טוֹבִים", "fp": "טוֹבוֹת"},
        needs_review=True,
    )
    decks = a_deck(entry)
    harvest(decks, [flagged_note("ball", "טוֹב", FLAG_GREEN)])
    assert entry.forms is not None and entry.forms["ms"] == "טוֹב"
    assert entry.hebrew is None


def test_an_empty_field_never_wipes_the_hebrew() -> None:
    """A blank field in Anki is far more likely a mistake than an intended deletion."""
    entry = an_entry()
    decks = a_deck(entry)
    harvest(decks, [flagged_note("ball", "   ", FLAG_GREEN)])
    assert entry.hebrew == "כָּדוּר"


def test_a_note_matching_nothing_is_reported_not_ignored() -> None:
    decks = a_deck(an_entry())
    result = harvest(decks, [flagged_note("ball", "כָּדוּר", FLAG_GREEN, deck_stem="verbs-paal")])
    assert result.changes == []
    assert len(result.unmatched) == 1


@pytest.mark.integration
def test_guids_index_the_real_decks_uniquely() -> None:
    """Harvest matches notes to entries by GUID, so collisions would misapply edits."""
    decks = load_all(DECKS_DIR)
    index = index_by_guid(decks)
    total = sum(len(deck.entries) for _, deck in decks)
    assert len(index) == total, "a GUID collision would let one note overwrite another"


@pytest.mark.integration
def test_harvest_against_the_real_deck_data() -> None:
    """Approving a real flagged entry clears it, and nothing else moves."""
    decks = load_all(DECKS_DIR)
    target = None
    for path, deck in decks:
        for entry in deck.entries:
            if entry.needs_review:
                target = (path, entry)
                break
        if target:
            break
    if target is None:
        # Every entry has been reviewed and approved. That is the goal state, not a
        # failure — the fixture this test needs simply no longer exists.
        pytest.skip("no flagged entries remain in the deck data")
    path, entry = target

    before = sum(1 for _, d in decks for e in d.entries if e.needs_review)
    note = RawNote(
        nid=1, deck="Modern Hebrew", notetype="MHF Noun",
        fields=(entry.hebrew or entry.lemma or "", entry.english),
        tags="src::mhf", guid=note_guid(path.stem, entry.id), flag=FLAG_GREEN,
    )
    result = harvest(decks, [note])

    assert entry.needs_review is False
    assert result.approved == 1
    after = sum(1 for _, d in decks for e in d.entries if e.needs_review)
    assert after == before - 1, "exactly one entry should have changed"


def test_an_english_edit_is_adopted() -> None:
    """Several entries are flagged for a gloss problem, not a pointing one."""
    entry = an_entry(english="decoration")
    decks = a_deck(entry)
    note = flagged_note("ball", "קִישׁוּטִי", FLAG_GREEN)
    note = RawNote(**{**note.__dict__, "fields": ("קִישׁוּטִי", "decorative", "", "", "", "", "")})
    result = harvest(decks, [note])
    assert entry.english == "decorative"
    assert result.changes[0].english_edited


def test_an_empty_english_field_never_wipes_the_gloss() -> None:
    entry = an_entry(english="ball")
    decks = a_deck(entry)
    note = flagged_note("ball", "כָּדוּר", FLAG_GREEN)
    note = RawNote(**{**note.__dict__, "fields": ("כָּדוּר", "  ", "", "", "", "", "")})
    harvest(decks, [note])
    assert entry.english == "ball"


def test_both_fields_can_change_at_once() -> None:
    entry = an_entry(hebrew="עשה", english="do")
    decks = a_deck(entry)
    note = flagged_note("ball", "עָשָׂה", FLAG_GREEN)
    note = RawNote(**{**note.__dict__, "fields": ("עָשָׂה", "do, make", "", "", "", "", "")})
    harvest(decks, [note])
    assert entry.hebrew == "עָשָׂה"
    assert entry.english == "do, make"


def test_orphans_are_detected() -> None:
    """Merging two entries leaves the loser's note behind in Anki forever."""
    from hebrew_cards.review import find_orphans

    decks = a_deck(an_entry())
    live = flagged_note("ball", "כָּדוּר", FLAG_NONE)
    stale = flagged_note("interrupt", "הִפְרִיע", FLAG_NONE)
    orphans = find_orphans(decks, [live, stale])
    assert len(orphans) == 1
    assert orphans[0].hebrew == "הִפְרִיע"


def test_no_orphans_when_everything_matches() -> None:
    decks = a_deck(an_entry())
    orphans_fn = __import__("hebrew_cards.review", fromlist=["find_orphans"]).find_orphans
    assert orphans_fn(decks, [flagged_note("ball", "כָּדוּר", FLAG_NONE)]) == []


def test_orange_flag_deletes_the_entry() -> None:
    """Deleting in Anki alone does not stick — the next import recreates the note."""
    from hebrew_cards.anki.collection import FLAG_ORANGE

    keep, drop = an_entry(id="interfere"), an_entry(id="interrupt-2")
    decks = a_deck(keep, drop)
    result = harvest(decks, [flagged_note("interrupt-2", "הִתְעָרֵב", FLAG_ORANGE)])

    assert [e.id for e in decks[0][1].entries] == ["interfere"]
    assert len(result.deleted) == 1
    assert result.deleted[0].entry_id == "interrupt-2"


def test_deleting_one_entry_leaves_its_neighbours_alone() -> None:
    from hebrew_cards.anki.collection import FLAG_ORANGE

    a, b, c = an_entry(id="a"), an_entry(id="b"), an_entry(id="c")
    decks = a_deck(a, b, c)
    harvest(decks, [flagged_note("b", "כָּדוּר", FLAG_ORANGE)])
    assert [e.id for e in decks[0][1].entries] == ["a", "c"]


def test_a_deleted_entry_is_not_also_counted_as_approved() -> None:
    from hebrew_cards.anki.collection import FLAG_ORANGE

    decks = a_deck(an_entry())
    result = harvest(decks, [flagged_note("ball", "כָּדוּר", FLAG_ORANGE)])
    assert result.approved == 0
    assert result.changes == []


def test_stale_notes_are_detected() -> None:
    """A note behind the YAML would revert the source edit if harvested."""
    from hebrew_cards.review import find_stale

    entry = an_entry(english="disturb, interrupt, interfere")
    decks = a_deck(entry)
    note = flagged_note("ball", "כָּדוּר", FLAG_NONE)
    note = RawNote(**{**note.__dict__, "fields": ("כָּדוּר", "disturb", "", "", "", "", "")})
    stale = find_stale(decks, [note])
    assert len(stale) == 1


def test_a_flagged_difference_is_not_stale() -> None:
    """On a flagged note a difference is the owner's edit, which is the whole point."""
    from hebrew_cards.review import find_stale

    entry = an_entry(english="disturb")
    decks = a_deck(entry)
    note = flagged_note("ball", "כָּדוּר", FLAG_GREEN)
    note = RawNote(**{**note.__dict__, "fields": ("כָּדוּר", "disturb, interfere", "", "", "", "", "")})
    assert find_stale(decks, [note]) == []


def test_matching_notes_are_not_stale() -> None:
    from hebrew_cards.review import find_stale

    entry = an_entry(english="ball")
    decks = a_deck(entry)
    note = flagged_note("ball", "כָּדוּר", FLAG_NONE)
    note = RawNote(**{**note.__dict__, "fields": ("כָּדוּר", "ball", "", "", "", "", "")})
    assert find_stale(decks, [note]) == []


def test_a_flagged_note_untouched_since_the_build_does_not_revert_the_yaml() -> None:
    """The merge-revert case: YAML moved on, Anki was never re-imported.

    The note is flagged green and its gloss differs from the YAML — which looks
    exactly like an edit to adopt. The build fingerprint says otherwise: Anki still
    holds precisely what the last build produced, so the owner never touched it, and
    the difference is the newer source edit. Adopting it would silently undo a merge.
    """
    entry = an_entry(english="disturb, interrupt, interfere")
    decks = a_deck(entry)
    note = flagged_note("ball", "כָּדוּר", FLAG_GREEN)
    note = RawNote(**{**note.__dict__, "fields": ("כָּדוּר", "disturb", "", "", "", "", "")})
    built = {note.guid: [["כָּדוּר", "disturb"]]}

    harvest(decks, [note], built)
    assert entry.english == "disturb, interrupt, interfere", "the merge was reverted"
    assert entry.needs_review is False, "the green verdict should still apply"


def test_a_genuine_anki_edit_is_still_adopted_with_a_build_state() -> None:
    """The fingerprint must not block real edits — only reverts."""
    entry = an_entry(english="do")
    decks = a_deck(entry)
    note = flagged_note("ball", "עָשָׂה", FLAG_GREEN)
    note = RawNote(**{**note.__dict__, "fields": ("עָשָׂה", "do, make", "", "", "", "", "")})
    built = {note.guid: [["עשה", "do"]]}   # what the build produced; Anki has moved on

    harvest(decks, [note], built)
    assert entry.english == "do, make"
    assert entry.hebrew == "עָשָׂה"


def test_stale_detection_covers_flagged_notes_when_a_build_state_exists() -> None:
    from hebrew_cards.review import find_stale

    entry = an_entry(english="disturb, interrupt, interfere")
    decks = a_deck(entry)
    note = flagged_note("ball", "כָּדוּר", FLAG_GREEN)
    note = RawNote(**{**note.__dict__, "fields": ("כָּדוּר", "disturb", "", "", "", "", "")})
    built = {note.guid: [["כָּדוּר", "disturb"]]}
    assert len(find_stale(decks, [note], built)) == 1


def test_any_past_build_value_counts_as_untouched() -> None:
    """The owner may be running an older build, not necessarily the latest.

    A single snapshot of the last build is not enough: rebuilding after a source edit
    moves the snapshot ahead of whatever the owner actually imported, and their
    unedited note then looks like an edit again. The history covers every build.
    """
    entry = an_entry(english="disturb, interrupt, interfere")
    decks = a_deck(entry)
    note = flagged_note("ball", "כָּדוּר", FLAG_GREEN)
    note = RawNote(**{**note.__dict__, "fields": ("כָּדוּר", "disturb", "", "", "", "", "")})
    built = {note.guid: [
        ["כָּדוּר", "disturb"],                            # an older build
        ["כָּדוּר", "disturb, interrupt, interfere"],      # the current one
    ]}
    harvest(decks, [note], built)
    assert entry.english == "disturb, interrupt, interfere"


def test_build_history_accumulates(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from hebrew_cards.build import read_build_history, record_build

    state = tmp_path / "build-state.jsonl"
    entry = an_entry()
    decks = a_deck(entry)
    for gloss in ("one", "two", "three"):
        entry.english = gloss
        record_build(decks, state)

    history = read_build_history(state)
    values = [v[1] for v in next(iter(history.values()))]
    assert values == ["one", "two", "three"], "every past build value is remembered"


def test_build_history_only_ever_appends(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Rewriting the file would defeat the union merge that keeps two machines apart."""
    from hebrew_cards.build import record_build

    state = tmp_path / "build-state.jsonl"
    entry = an_entry()
    decks = a_deck(entry)
    record_build(decks, state)
    first = state.read_text(encoding="utf-8")

    entry.english = "changed"
    record_build(decks, state)
    second = state.read_text(encoding="utf-8")

    assert second.startswith(first), "existing lines must never be rewritten"
    assert len(second.splitlines()) == len(first.splitlines()) + 1


def test_rebuilding_unchanged_data_adds_nothing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Otherwise every build would grow the file and churn the diff for no reason."""
    from hebrew_cards.build import record_build

    state = tmp_path / "build-state.jsonl"
    decks = a_deck(an_entry())
    record_build(decks, state)
    before = state.read_text(encoding="utf-8")
    record_build(decks, state)
    assert state.read_text(encoding="utf-8") == before


def test_duplicate_lines_from_a_union_merge_are_tolerated(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Union merge keeps both sides, so the same record can appear twice."""
    from hebrew_cards.build import read_build_history, record_build

    state = tmp_path / "build-state.jsonl"
    decks = a_deck(an_entry())
    record_build(decks, state)
    doubled = state.read_text(encoding="utf-8")
    state.write_text(doubled + doubled, encoding="utf-8")

    history = read_build_history(state)
    assert len(next(iter(history.values()))) == 1, "duplicates collapse on load"
