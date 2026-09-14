#!/usr/bin/env python3
"""Extract Modern Hebrew notes from the Anki collection into deck YAML.

Reads a *copy* of the collection (never the live file) and writes one YAML file
per source deck under data/decks/. Only `Modern Hebrew::*` decks are touched.

Usage:
    python scripts/extract_collection.py [--out data/decks] [--scratch DIR] [--dry-run]
"""

from __future__ import annotations

import argparse
import collections
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))

from hebrew_cards.anki import collection as col          # noqa: E402
from hebrew_cards.anki.extract import (  # noqa: E402
    DECK_RULES, assign_ids, dedupe, extract_note,
)
from hebrew_cards.models import DeckFile, DeckMeta       # noqa: E402
from hebrew_cards.yamlio import dump_deck                # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=_REPO / "data" / "decks")
    parser.add_argument("--scratch", type=Path, default=None,
                        help="where to copy the collection (default: a temp dir)")
    parser.add_argument("--keep-duplicates", action="store_true",
                        help="keep notes identical in both Hebrew and gloss "
                             "(default: collapse them to one)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be written without writing it")
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing deck files (discards hand edits)")
    args = parser.parse_args()

    existing = sorted(p.name for p in args.out.glob("*.yaml")) if args.out.exists() else []
    if existing and not args.force and not args.dry_run:
        print(
            f"\nERROR: {args.out} already contains {len(existing)} deck files.\n"
            "Extraction is a one-time migration — data/decks/ is the source of truth now,\n"
            "and re-running would discard any hand edits made since. Pass --force if that\n"
            "is genuinely what you want.",
            file=sys.stderr,
        )
        return 1

    scratch = args.scratch or Path(tempfile.mkdtemp(prefix="hebrew-cards-"))
    copy = col.copy_collection(scratch / "collection.anki2")
    notes = col.read_notes(copy)
    print(f"read {len(notes)} in-scope notes from {copy}")

    unknown = sorted({n.deck for n in notes if n.deck not in DECK_RULES})
    if unknown:
        print("\nERROR: no extraction rule for these in-scope decks:")
        for deck in unknown:
            print(f"  {deck}")
        return 1

    by_deck: dict[str, list[col.RawNote]] = collections.defaultdict(list)
    for note in notes:
        by_deck[note.deck].append(note)

    decks: list[DeckFile] = []
    total_dropped = 0
    for deck_name in sorted(by_deck):
        rule = DECK_RULES[deck_name]
        entries = [extract_note(n, rule) for n in by_deck[deck_name]]
        if not args.keep_duplicates:
            entries, dropped = dedupe(entries)
            total_dropped += dropped
        assign_ids(entries)
        meta = DeckMeta(
            name=deck_name.split("::", 1)[1],
            source_deck=deck_name,
            card_types=["audio_meaning"],
        )
        if rule.filename == "verbs-general":
            meta.notes.append(
                "Source deck mixes parts of speech — it contains adverbs "
                "(תֵכֶף 'instantaneously', בְּפֵרוּשׁ 'clearly') alongside verbs. "
                "Entries whose gloss looks adverbial are flagged; the rest still "
                "need a pass."
            )
        decks.append(DeckFile(meta=meta, entries=entries))

    if total_dropped:
        print(f"\ncollapsed {total_dropped} exact duplicate notes "
              f"(identical Hebrew and gloss)")
    _report(decks)

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    for deck in decks:
        rule = DECK_RULES[deck.meta.source_deck or ""]
        path = args.out / f"{rule.filename}.yaml"
        path.write_text(dump_deck(deck), encoding="utf-8")
        print(f"wrote {path.relative_to(_REPO)}  ({len(deck.entries)} entries)")
    return 0


def _report(decks: list[DeckFile]) -> None:
    """Print a summary of what was extracted and what needs attention."""
    total = sum(len(d.entries) for d in decks)
    if not total:
        print("\nNo entries extracted — no legacy Modern Hebrew notes remain.")
        return
    flagged = [e for d in decks for e in d.entries if e.needs_review]
    print(f"\n{total} entries, {len(flagged)} flagged for review "
          f"({len(flagged) / total:.0%})")

    reasons: collections.Counter[str] = collections.Counter()
    for entry in flagged:
        for note in entry.review_notes:
            key = note.split("(")[0].split(",")[0].strip()
            reasons[key] += 1
    print("\nreasons:")
    for reason, count in reasons.most_common():
        print(f"  {count:4d}  {reason}")

    # Duplicate Hebrew across the whole extraction, not just within a deck.
    seen: dict[str, list[str]] = collections.defaultdict(list)
    for deck in decks:
        for entry in deck.entries:
            form = entry.hebrew or entry.lemma or ""
            if form:
                seen[form].append(f"{deck.meta.name}/{entry.id}")
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    if dupes:
        print(f"\n{len(dupes)} Hebrew forms appear in more than one entry:")
        for form, where in sorted(dupes.items())[:20]:
            print(f"  {form}  ->  {', '.join(where)}")
        if len(dupes) > 20:
            print(f"  ... and {len(dupes) - 20} more")


if __name__ == "__main__":
    raise SystemExit(main())
