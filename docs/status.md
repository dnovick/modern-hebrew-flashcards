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
  `Modern Hebrew` deck root. 396 entries across 13 deck files.
- **Review loop.** Flag cards in Anki, `scripts/harvest_review.py --apply` pulls the
  verdicts into the YAML. Green = correct, orange = delete the entry, red = still
  wrong, unflagged = leave alone.
- **First review pass complete.** All 38 originally-flagged entries resolved: 24
  pointings confirmed, 3 duplicates deleted, 2 entries merged, 3 refiled into the
  right decks.
- **Deck hierarchy reorganized (2026-09-14).** Deck names are now POS-first, with
  topic sub-decks only where a real cluster exists: `Adjectives::Human Attributes`
  (was a standalone `Human Attributes` deck — those 99 entries are adjectives, so
  they now nest under `Adjectives`), `Nouns::Fruit` (was standalone `Fruit`). The
  two modal files (`modals.yaml`, and the mislabeled `verbs-modal.yaml` — its 15
  entries are `pos: modal`, not verbs) were merged into one `modals.yaml`/`Modals`
  deck. Full tree now: `Nouns` (+`::Fruit`), `Adjectives` (+`::Human Attributes`),
  `Verbs::{Paal,Niphal,Piel,Hiphil,Hitpael,General}`, `Modals`, `Adverbs`,
  `Prepositions` — 13 deck files, 396 entries, unchanged. All renames except the
  modal merge only touched `meta.name` (deck slugs/GUIDs unaffected, since GUIDs key
  off the YAML filename, not the deck name); the modal merge changes GUIDs for those
  15 entries, adding to the orphan cleanup below.

## In progress

**85 noun gender proposals await review.** Every noun in `nouns.yaml` and `fruit.yaml`
has a proposed `gender` and is flagged `needs_review`. Search `tag:needs-review` in
Anki; the gender shows on the answer side. Multi-select and flag in bulk — most are
obvious from the ending.

Five carry a second note worth reading before deciding: `קִישׁוּטִי` (adjective, not a
noun — gender left unset), `תֵיוּץ` (likely a typo for `תֵּירוּץ`), `תַכְשִׁיטִים` and
`חִסְכוֹנוֹת` (stored as plurals; an `-ot` plural does not make a noun feminine), and
`פִּירָה` (loanword, lower confidence).

**Orphan notes to delete in Anki after the next import** — imports never delete
notes, so a rebuild leaves the old copies behind whenever an entry's GUID changes.

- Three from the earlier refiling:

      English:"instantaneously" OR English:"clearly" OR English:"look, contemplate"

  filtered to `deck:"Modern Hebrew::Verbs::General"` so the new copies are not caught.

- Fifteen from the 2026-09-14 modals merge, findable as the notes still sitting in
  `deck:"Modern Hebrew::Verbs::Modal"` after import (the rebuilt deck is
  `Modern Hebrew::Modals`; the old `Verbs::Modal` deck should end up empty and can be
  deleted along with its notes).

1. **Organizing the corpus (current focus, 2026-09-14 owner request).** The deck
   hierarchy reorg above is the first step. Remaining: classify the 40
   `Verbs::General` entries into their binyan sub-decks; decide whether `Nouns` (79
   entries, no strong topical clusters beyond `Fruit`) is worth splitting further as
   more nouns are added.
2. **Remaining enrichment.** Noun plurals, adjective agreement forms beyond the
   feminine already captured, verb roots and binyanim, then paradigms.
3. **New topic decks.** See the README's deck topics list.
4. **Audio — deprioritized (2026-09-14 owner request).** Google Cloud TTS, Chirp 3
   HD, he-IL. Needs a GCP project with billing enabled and
   `GOOGLE_APPLICATION_CREDENTIALS` pointing at a service account key. Adds the
   audio-fronted card to every note, roughly doubling the card count. Under a dollar
   for the whole deck — revisit once the corpus organization work above settles.

## Setting up another machine

    git clone git@github.com:dnovick/modern-hebrew-flashcards.git
    cd modern-hebrew-flashcards
    python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python -m pytest

`dist/` and `.venv` are gitignored and do not travel — rebuild the package rather than
looking for it. The Anki collection is not in git either; the owner syncs it through
AnkiWeb, and card flags sync with it.
