---
type: status
scope: modern-hebrew-flashcards
updated: 2026-09-15
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
- **Noun gender review complete (2026-09-15).** All 85 proposed genders resolved: 83
  confirmed via green flag and harvested normally. Five needed more than a flag and
  were fixed by hand per the owner's call: `decoration` → moved to `adjectives.yaml`
  as `decorative` (קִישׁוּטִי); it was never a noun and is still `needs_review` there —
  only the ms form is known, fs/mp/fp aren't. `jewelry` and `savings` were restored
  to their singular (תַּכְשִׁיט, חִסָּכוֹן) with a `plural:` field, instead of storing only
  the plural. `excuse`'s typo was fixed (תֵיוּץ → תֵּירוּץ). `mashed-potatoes` confirmed
  m via the normal flag/harvest path.
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

**One adjective still needs review.** `decorative` (קִישׁוּטִי, in `adjectives.yaml`) is
tagged `needs_review` — only its ms citation form is recorded; fs/mp/fp aren't
confirmed. Low priority, tracked under "remaining enrichment" below rather than as
its own effort.

All orphan cleanup from the deck reorg and the gender-review fixes is done — the
collection currently has zero orphans (`scripts/harvest_review.py` reports this).

## Next

1. **Organizing the corpus (current focus, 2026-09-14 owner request).** The deck
   hierarchy reorg above is the first step. Remaining: classify the 40
   `Verbs::General` entries into their binyan sub-decks; decide whether `Nouns` (78
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
