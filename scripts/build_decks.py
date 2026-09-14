#!/usr/bin/env python3
"""Build deck YAML into an Anki package.

Writes a single .apkg containing every deck. Nothing is written to the live Anki
collection — import the file by hand.

Usage:
    python scripts/build_decks.py [--decks data/decks] [--out dist/modern-hebrew.apkg]
                                  [--deck-root "Modern Hebrew (rebuild)"]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))

from hebrew_cards.build import (  # noqa: E402
    DEFAULT_DECK_ROOT, build_package, build_state_path,
)
from hebrew_cards.loader import DeckLoadError, load_all          # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decks", type=Path, default=_REPO / "data" / "decks")
    parser.add_argument("--out", type=Path, default=_REPO / "dist" / "modern-hebrew.apkg")
    parser.add_argument("--deck-root", default=DEFAULT_DECK_ROOT)
    args = parser.parse_args()

    try:
        decks = load_all(args.decks)
    except DeckLoadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    stats = build_package(decks, args.out, args.deck_root, build_state_path(_REPO))
    print(f"built {stats.notes} notes across {stats.decks} decks")
    for skipped in stats.skipped:
        print(f"  skipped {skipped}")
    print(f"\nwrote {args.out}")
    print(f"deck root: {args.deck_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
