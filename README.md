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

So the project adds a card type the old decks never had: **audio on the front, with
nothing to read**. It sits alongside the written-Hebrew cards rather than replacing
them — reading and listening are different skills, and only one of them is the gap.

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
| **Hebrew → meaning** | pointed Hebrew | English + grammar detail | reading recognition |
| **Audio → meaning** | audio only | English + pointed Hebrew | listening recognition |
| **Sentence dictation** | sentence audio | full sentence text | parsing connected speech |
| **Audio cloze** | sentence audio, one word blanked | the missing word | hearing a word in context |
| Minimal pairs | two clips | which one was X | phoneme discrimination |
| Conjugation by ear | conjugated-form audio | person/number/tense + root | morphology at speed |
| Gender ID | noun audio | m / f | agreement, which gender governs |
| Plural production | singular audio | the plural form | irregular plurals |
| Adjective agreement | citation + target form | the agreeing form | the four-form pattern |
| Root family | a root | the words derived from it | guessing unknown words by ear |

Production cards (English → Hebrew) are deliberately **not** generated — both
vocabulary cards above are recognition, and production is a separate skill.

Audio-fronted cards are what the old decks were missing, but they are additions, not
replacements. A word with audio gets two cards: one read, one heard.

## Data model

Notes carry full linguistic metadata — gender and plural for nouns, all four agreement
forms for adjectives, root/binyan/gizra and complete paradigms for verbs — so that many
card types can be generated from one authoritative entry. See
[`docs/standards/data-model.md`](docs/standards/data-model.md).

Two ideas carry most of the weight:

- **Store everything, drill a subset.** A verb's full paradigm lives in YAML; its
  `drill:` list decides which forms become cards. Storage is free, review time isn't.
- **Staged card generation.** The full card matrix over the 400 extracted entries is
  ~1,800 cards, about 3.5× the current review load. Each deck's `meta.card_types`
  controls which types are live, so metadata can be complete long before every card
  type is switched on.

## Deck topics

**Migrated first** (from the existing collection, 457 notes → 400 unique entries):
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

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt

.venv/bin/python scripts/extract_collection.py   # Anki collection -> data/decks/*.yaml
.venv/bin/python scripts/build_decks.py          # data/decks/*.yaml -> dist/*.apkg
.venv/bin/python -m pytest                       # 71 tests
.venv/bin/python scripts/check_coverage.py       # coverage ratchet
```

`build_decks.py` writes `dist/modern-hebrew.apkg` under the `Modern Hebrew` deck
root. Import it by hand — nothing here ever writes to your live collection.

> **Audio is not generated yet**, so only the Hebrew-front cards exist today. The
> audio-front template is already in place and gated on the `Audio` field, so those
> cards appear by themselves once audio lands — no rebuild of the data, no config
> change. Expect the card count to roughly double at that point.

Milestones:

1. ~~Extract the existing `Modern Hebrew::*` notes to YAML.~~ **Done** — 457
   notes extracted to 400 unique entries across 14 deck files.
2. ~~Stand up the build: YAML → validated models → `.apkg`.~~ **Done** — 400 notes
   across 14 decks, with a test proving two builds produce identical GUIDs so a
   re-import updates rather than duplicates.
3. Add the TTS layer and regenerate the decks with audio. **Next.**
4. Add audio-fronted note types and rebuild.
5. Start authoring new topic decks.

## Migration

Done. The legacy decks were extracted to YAML, rebuilt, verified, and deleted; the
generated decks now live at `Modern Hebrew::*` and are the only Modern Hebrew decks
in the collection.

Because generated decks now carry the names the source decks had, deck name no longer
distinguishes them. Two markers do, and extraction depends on them:

| Marker | Generated notes |
|---|---|
| Note type | `MHF Noun`, `MHF Adjective`, `MHF Verb`, `MHF Particle` |
| Tag | `src::mhf` |

`scripts/extract_collection.py` skips any note matching either, so re-running it can
never fold the pipeline's own output back into its source data. It also refuses to
overwrite `data/decks/` without `--force`.

## Reviewing flagged entries

Extraction flags anything it could not vouch for — unpointed Hebrew, a gloss that
looks misfiled, two entries claiming the same word. Those carry `needs_review` in the
YAML and a `needs-review` tag in Anki. Search `tag:needs-review` to find them.

Review them in Anki and record each verdict with a flag:

| Flag | Means |
|---|---|
| **Green** (`⌘3` on macOS, `Ctrl+3` elsewhere) | correct as it stands — clears the flag |
| **Red** (`⌘1` / `Ctrl+1`) | still wrong — keeps it flagged for another pass |

Anki is a Qt application, so every shortcut its docs spell `Ctrl+N` is `⌘N` on macOS.
The menu route always works: select the rows, then right-click → Flag, or Cards → Flag.

Fix the Hebrew or the English directly in the Anki editor where either needs changing;
the harvest picks both up along with the flag. Then:

```bash
.venv/bin/python scripts/harvest_review.py            # show what it would do
.venv/bin/python scripts/harvest_review.py --apply    # write it to the YAML
.venv/bin/python scripts/build_decks.py               # rebuild
```

Unflagged cards are left completely alone, so an accidental edit in the browser can
never rewrite the source data — only an explicit verdict does.

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
| Migration | staged under a separate root, then renamed | originals stayed reviewable until deleted; complete as of 2026-09-13 |
