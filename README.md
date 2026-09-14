# modern-hebrew-flashcards

Version-controlled source data and a Python build pipeline that generates Modern
Hebrew Anki decks — with generated Hebrew audio on every card.

**Status:** design phase. No code yet. `CLAUDE.md` holds the working rules;
this file holds the plan.

## Why this exists

The goal is not "more vocabulary." Vocabulary and grammar are already in decent
shape. The gap is **listening comprehension** — recognizing known words at
conversational speed, in connected speech, spoken by a voice you have not heard
before.

Existing Anki decks do not help with that, because they have no audio and are
mostly English→Hebrew recognition. Reading `כָּדוּר` and recalling "ball" is a
different skill from hearing that word in a sentence and not stalling.

So this project inverts the default: **audio is the front of the card**, text is
the answer.

## Architecture

```
data/decks/*.yaml   →   validate   →   TTS (cached)   →   genanki   →   dist/*.apkg
   (source of truth)                    media/                          (manual import)
```

- **YAML is the source of truth.** Anki is a rendering target. Decks are rebuilt
  from data; data is never recovered from Anki after the initial extraction.
- **`.apkg` output only.** The build never writes to the live Anki collection.
- **Deterministic GUIDs.** Re-importing a rebuilt deck updates its notes in
  place rather than duplicating them. (Review history from the *old* decks is not
  carried over — that was a deliberate trade for a clean data model.)
- **Cached, content-addressed audio.** Changing one translation does not
  regenerate (or re-bill) a thousand audio clips.

### Planned layout

```
src/hebrew_cards/
  models.py       Pydantic models for entries, decks, note types
  loader.py       YAML load + validation with useful error locations
  hebrew.py       nikud normalization, plain-form derivation, validation
  notetypes.py    Anki note type definitions (stable IDs, HTML templates, CSS)
  tts/            provider interface + cloud backend + fake for tests
  build.py        genanki deck assembly
  anki/extract.py one-time read-only extraction from the existing collection
  cli.py          `hebrew-cards validate | build | extract | audio`
scripts/
  report_flagged.py  map red-flagged Anki cards back to their YAML entries
data/decks/       one YAML file per topic deck
media/            audio cache (gitignored)
dist/             built .apkg files (gitignored)
tests/
```

## Card types

Beyond plain vocabulary, these are the formats that actually target the stated gap:

| Type | Front | Back | Trains |
|---|---|---|---|
| **Audio → meaning** | audio only | English + pointed Hebrew | core listening recognition |
| **Sentence dictation** | sentence audio | full sentence text | parsing connected speech |
| **Audio cloze** | sentence audio, one word blanked | the missing word | hearing a word in context |
| Minimal pairs | two clips | which one was X | phoneme discrimination |
| Conjugation by ear | conjugated-form audio | person/number/tense + root | morphology at speed |
| Gender ID | noun audio | m / f | agreement, which gender governs |
| Plural production | singular audio | the plural form | irregular plurals |
| Adjective agreement | citation + target form | the agreeing form | the four-form pattern |
| Root family | a root | the words derived from it | guessing unknown words by ear |

The audio-fronted types are the point of the project. Production cards
(English → Hebrew) are deliberately **not** generated — the gap is recognition.

For vocabulary, one card is generated per entry: audio on the front with no visible
text of any kind, English plus the pointed Hebrew on the back.

## Data model

Notes carry full linguistic metadata — gender and plural for nouns, all four agreement
forms for adjectives, root/binyan/gizra and complete paradigms for verbs — so that many
card types can be generated from one authoritative entry. See
[`docs/standards/data-model.md`](docs/standards/data-model.md).

Two ideas carry most of the weight:

- **Store everything, drill a subset.** A verb's full paradigm lives in YAML; its
  `drill:` list decides which forms become cards. Storage is free, review time isn't.
- **Staged card generation.** The full card matrix over the existing 516 notes is
  ~2,100 cards, about 4× the current review load. Each deck's `meta.card_types`
  controls which types are live, so metadata can be complete long before every card
  type is switched on.

## Deck topics

**Migrated first** (from the existing collection, ~516 cards):
nouns · verbs by binyan (paal, piel, hiphil, niphal, hitpael) · adjectives ·
adverbs · prepositions · modals · fruit · human attributes

**Proposed vocabulary topics:**
food & cooking · the body & health · home and furniture · clothing · transit and
directions · work and office · money and shopping · weather and seasons ·
family and relationships · emotions · time expressions · city and bureaucracy ·
technology and phones · army and news vocabulary · animals · school and study

**Proposed non-vocabulary decks** — these are where the listening gains are:

- **Numbers, dates, times, prices** — spoken numbers are disproportionately hard
  and disproportionately common. Audio-only, answer is the digits.
- **Connected speech and reductions** — how Hebrew is actually pronounced vs.
  written: dropped אני, swallowed ה, מה זה → *ma ze* run together.
- **Prepositional pronouns** — עליי / עליך / עליו, לי / לך / לו, אצלי, ממנו.
  Paradigm tables, drilled by ear.
- **Discourse markers and fillers** — בעצם, בכלל, כאילו, דווקא, נו. Ubiquitous in
  speech, rare in textbooks, and they carry the sentence's attitude.
- **Construct chains (סמיכות)** — recognizing them mid-sentence.
- **Root families** — one שורש, the words derived from it across binyanim.
  Builds the pattern recognition that lets you guess unknown words by ear.
- **Question → natural answer pairs** — heard as dialogue, not isolated words.
- **Sentence decks graded by speed** — same sentence at normal and fast rates.

## Getting started

Nothing to run yet. First milestones, in order:

1. Extract the existing `Modern Hebrew::*` notes to YAML, normalized and
   de-junked (the current tags contain leaked Apple Notes metadata).
2. Stand up the build: YAML → validated models → `.apkg`, with GUID stability
   tests proving a rebuild updates rather than duplicates.
   Builds land under a `Modern Hebrew (rebuild)` deck root so the originals stay
   untouched and reviewable side by side — see *Migrating the existing decks*.
3. Add the TTS layer and regenerate the migrated decks with audio.
4. Add audio-fronted note types and rebuild.
5. Start authoring new topic decks.

## Migrating the existing decks

The rebuilt notes do not match the current ones, so importing puts both sets in
the collection at once. Three markers keep them apart, any one of which is
sufficient to select exactly the right cards:

| Marker | Old cards | New cards |
|---|---|---|
| Deck | `Modern Hebrew::*` | `Modern Hebrew (rebuild)::*` |
| Note type | `Basic`, `Basic_2_fields`, `Basic (and reversed card)` | `MHF *` |
| Tag | — | `src::mhf` |

The procedure:

1. The old decks are exported to `archive/modern-hebrew-<date>.apkg` first, so
   deleting them is reversible.
2. New decks import under `Modern Hebrew (rebuild)`, leaving the originals alone.
3. Review the two side by side.
4. Delete the `Modern Hebrew` tree and rename `Modern Hebrew (rebuild)` to
   `Modern Hebrew`. Renaming a deck does not affect its cards.
5. Flip the configured deck root back to `Modern Hebrew` for future builds.

Steps 1 and 4 happen by hand in the Anki UI. This project never deletes decks.

## Fixing a card you spot mid-review

YAML is the source of truth, so an edit made in Anki's editor is overwritten by the
next rebuild. Instead:

| Step | Where |
|---|---|
| 1. Flag the card **red** (`Ctrl+1`), keep reviewing | Anki |
| 2. `scripts/report_flagged.py` maps red flags back to source entries by GUID | terminal |
| 3. Fix the entry, rebuild, re-import | `data/decks/*.yaml` |
| 4. Clear the flag | Anki |

Red means *content bug, fix in source* — nothing else. No flag was in use anywhere in
the collection when this was adopted, so the meaning is unambiguous.

## Development

Conventions follow [`berean-bible-bots`](https://github.com/dnovick/berean-bible-bots)
(Foundry-derived), scaled down for a solo project:

- Python 3.12, src-layout, `requirements.txt`
- `flake8` + `mypy` clean before every commit — config in `setup.cfg`
- `pytest` with an `integration` marker for anything needing network or paid TTS;
  the default run makes no network calls and spends no credit
- Coverage tracked by a **must-not-decrease ratchet** against `coverage-baseline.json`
- Direct pushes to `main` are fine (solo repo, no branch protection); feature
  branches for anything substantial enough to review as a unit
- Content rules in [`docs/standards/language.md`](docs/standards/language.md) —
  notably: Hebrew script with nikud everywhere, no transliteration
- Agent autonomy is governed by [`docs/policies/autonomous-actions.md`](docs/policies/autonomous-actions.md)

Behavioral tests are the bar for "done": a build capability must be observed producing
a real `.apkg` with correct contents, not merely reviewed.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| TTS | Google Cloud, Chirp 3 HD (he-IL) | best available Hebrew quality; cost is negligible at this volume (<$1 for the full deck) |
| Existing cards | extract → clean → rebuild, fresh GUIDs | clean data model; review history deliberately not carried over |
| Delivery | `.apkg` files, manual import | works headless and in CI; no add-on dependency |
| Language | Python 3.12 | project policy |
| Conventions | inherited from `berean-bible-bots` | consistency across the owner's projects |
| Scope | `Modern Hebrew::*` only | other decks are a separate area of study |
| Migration | staged under a separate deck root | originals stay reviewable until you delete them yourself |
