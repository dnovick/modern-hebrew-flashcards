---
type: status
scope: modern-hebrew-flashcards
updated: 2026-09-14
---

# Where the project stands

A running handoff note, kept in the repo because sessions do not carry between
machines. Update it when the answer to "what was I in the middle of" changes.

## Done

- **Extraction.** 457 legacy Anki notes → 400 entries in `data/decks/*.yaml`. The
  legacy decks have been deleted; there is no source left to re-extract.
- **Build.** `scripts/build_decks.py` produces `dist/modern-hebrew.apkg` under the
  `Modern Hebrew` deck root. 396 entries across 14 deck files.
- **Review loop.** Flag cards in Anki, `scripts/harvest_review.py --apply` pulls the
  verdicts into the YAML. Green = correct, orange = delete the entry, red = still
  wrong, unflagged = leave alone.
- **First review pass complete.** All 38 originally-flagged entries resolved: 24
  pointings confirmed, 3 duplicates deleted, 2 entries merged, 3 refiled into the
  right decks.

## In progress

**85 noun gender proposals await review.** Every noun in `nouns.yaml` and `fruit.yaml`
has a proposed `gender` and is flagged `needs_review`. Search `tag:needs-review` in
Anki; the gender shows on the answer side. Multi-select and flag in bulk — most are
obvious from the ending.

Five carry a second note worth reading before deciding: `קִישׁוּטִי` (adjective, not a
noun — gender left unset), `תֵיוּץ` (likely a typo for `תֵּירוּץ`), `תַכְשִׁיטִים` and
`חִסְכוֹנוֹת` (stored as plurals; an `-ot` plural does not make a noun feminine), and
`פִּירָה` (loanword, lower confidence).

**Three orphan notes to delete in Anki**, left behind by the refiling — imports never
delete notes. Find them with:

    English:"instantaneously" OR English:"clearly" OR English:"look, contemplate"

filtered to `deck:"Modern Hebrew::Verbs::General"` so the new copies are not caught.

## Next

1. **Audio.** Google Cloud TTS, Chirp 3 HD, he-IL. Needs a GCP project with billing
   enabled and `GOOGLE_APPLICATION_CREDENTIALS` pointing at a service account key.
   Adds the audio-fronted card to every note, roughly doubling the card count.
   Under a dollar for the whole deck.
2. **Remaining enrichment.** Noun plurals, adjective agreement forms beyond the
   feminine already captured, verb roots and binyanim, then paradigms.
3. **New topic decks.** See the README's deck topics list.

## Setting up another machine

    git clone git@github.com:dnovick/modern-hebrew-flashcards.git
    cd modern-hebrew-flashcards
    python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python -m pytest

`dist/` and `.venv` are gitignored and do not travel — rebuild the package rather than
looking for it. The Anki collection is not in git either; the owner syncs it through
AnkiWeb, and card flags sync with it.
