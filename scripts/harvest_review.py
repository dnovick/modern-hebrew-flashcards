#!/usr/bin/env python3
"""Pull review decisions made in Anki back into the deck YAML.

Review flagged cards in Anki, then mark each one:

    green (Cmd+3 on macOS, Ctrl+3 elsewhere)  correct as it stands — clears the flag
    red   (Cmd+1 / Ctrl+1)                    still wrong — keeps it flagged

The menu route always works too: select rows, right-click -> Flag, or Cards -> Flag.

Edit the Hebrew or the English directly in Anki if either needs changing; this picks
both up along with the flag. Unflagged cards are left completely alone.

Reports what it would do by default. Pass --apply to write the YAML.

Usage:
    python scripts/harvest_review.py            # dry run
    python scripts/harvest_review.py --apply
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))

from hebrew_cards.anki import collection as col       # noqa: E402
from hebrew_cards.loader import DeckLoadError, load_all  # noqa: E402
from hebrew_cards.review import find_orphans, harvest  # noqa: E402
from hebrew_cards.yamlio import dump_deck             # noqa: E402


def _print_status(notes: list[col.RawNote]) -> None:
    """Report review progress, so it can be checked without hunting through the UI."""
    awaiting = [n for n in notes if "needs-review" in n.tags.split()]
    green = [n for n in notes if n.flag == col.FLAG_GREEN]
    red = [n for n in notes if n.flag == col.FLAG_RED]
    undecided = [n for n in awaiting if n.flag == col.FLAG_NONE]

    print(f"{len(notes)} generated notes in the collection")
    print(f"  {len(awaiting):4d} tagged needs-review")
    print(f"  {len(green):4d} flagged green  (correct)        [search: flag:3]")
    print(f"  {len(red):4d} flagged red    (still wrong)    [search: flag:1]")
    print(f"  {len(undecided):4d} still undecided                [search: tag:needs-review flag:0]")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decks", type=Path, default=_REPO / "data" / "decks")
    parser.add_argument("--apply", action="store_true", help="write the changes")
    args = parser.parse_args()

    try:
        decks = load_all(args.decks)
    except DeckLoadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    scratch = Path(tempfile.mkdtemp(prefix="hebrew-cards-review-"))
    copy = col.copy_collection(scratch / "collection.anki2")
    notes = col.read_notes(copy, generated=True)
    _print_status(notes)

    orphans = find_orphans(decks, notes)
    if orphans:
        print(f"\n{len(orphans)} note(s) in Anki no longer have an entry in the deck data.")
        print("Importing never deletes notes, so these linger until removed by hand:")
        for orphan in orphans:
            print(f'   {orphan.deck}   {orphan.hebrew}  "{orphan.english}"')
        print("Find them in the browser by their text and delete them.")

    result = harvest(decks, notes)

    if not result.changes:
        print("\nNothing flagged yet. In the Anki browser, search tag:needs-review and mark\n"
              "each card green (correct) or red (still wrong) — Cmd+3 / Cmd+1 on macOS,\n"
              "Ctrl+3 / Ctrl+1 elsewhere, or right-click -> Flag.")
        return 0

    print(f"\n{result.approved} approved, {result.edits} with edited Hebrew:\n")
    for change in result.changes:
        mark = "approved " if change.verdict == "approved" else "flagged  "
        print(f"  {mark} {change.deck}/{change.entry_id}")
        if change.hebrew_edited:
            print(f"             hebrew:  {change.old_hebrew}  ->  {change.new_hebrew}")
        if change.english_edited:
            print(f"             english: {change.old_english!r}  ->  {change.new_english!r}")

    for problem in result.unmatched:
        print(f"  UNMATCHED {problem}")

    if not args.apply:
        print("\n(dry run — pass --apply to write)")
        return 0

    for path, deck in decks:
        path.write_text(dump_deck(deck), encoding="utf-8")
    print(f"\nwrote {len(decks)} deck files")
    print("Clear the flags in Anki, then rebuild:  python scripts/build_decks.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
