#!/usr/bin/env python3
"""Pull review decisions made in Anki back into the deck YAML.

Review flagged cards in Anki, then mark each one:

    green (Ctrl+3)  correct as it now stands — clears the review flag
    red   (Ctrl+1)  still wrong — keeps it flagged for another pass

Edit the Hebrew field directly in Anki if it needs changing; this picks the edit up
along with the flag. Unflagged cards are left completely alone.

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
from hebrew_cards.review import harvest               # noqa: E402
from hebrew_cards.yamlio import dump_deck             # noqa: E402


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
    flagged = [n for n in notes if n.flag != col.FLAG_NONE]
    print(f"{len(notes)} generated notes in the collection, {len(flagged)} flagged")

    result = harvest(decks, notes)

    if not result.changes:
        print("\nNothing flagged. Flag cards green (correct) or red (still wrong) in Anki first.")
        return 0

    print(f"\n{result.approved} approved, {result.edits} with edited Hebrew:\n")
    for change in result.changes:
        mark = "approved " if change.verdict == "approved" else "flagged  "
        line = f"  {mark} {change.deck}/{change.entry_id}"
        if change.edited:
            line += f"   {change.old_hebrew}  ->  {change.new_hebrew}"
        print(line)

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
