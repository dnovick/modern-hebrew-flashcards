# CLAUDE.md — modern-hebrew-flashcards

Guidance for Claude Code working in this repository.

## What this project is

A build pipeline that turns version-controlled YAML vocabulary/sentence data into
Anki `.apkg` decks for Modern Hebrew, with generated Hebrew audio on every card.

The owner already has solid Hebrew vocabulary and grammar. **The bottleneck is
listening comprehension.** Every design decision should be weighed against that:
if a card can be made to train the ear rather than the eye, it should be.

## Hard rules

1. **Never modify the live Anki collection.** `~/Library/Application Support/Anki2/`
   is read-only input. To inspect it, copy `collection.anki2` to the scratchpad and
   query the copy. All output goes to `dist/*.apkg` for manual import.
2. **Only `Modern Hebrew::*` decks are in scope.** The collection also contains
   `BBH::*`, `BBG::*`, `Biblical Hebrew::*`, and `Psalm 119::*`. Those belong to a
   separate area of study. Do not read them into this project's data, do not
   reference them in generated decks, do not touch them.
3. **All code is Python.** No shell scripts beyond thin wrappers, no JS/TS.
4. **YAML under `data/` is the source of truth.** Anki is a rendering target, never
   an authority. If data only exists in Anki, extract it to YAML first.
5. **Never invent Hebrew.** Vocabulary, nikud, gender, and binyan classification must
   be correct. When uncertain about a form, mark it `needs_review: true` in the YAML
   rather than guessing. A confidently wrong card is worse than a missing one.
6. **Deterministic builds.** Same input YAML + same media cache → byte-identical
   deck contents. No timestamps or randomness in note IDs or GUIDs.

## Note GUIDs

Anki matches notes on import by GUID. Review history is explicitly **not**
preserved — the existing Modern Hebrew cards are being rebuilt from scratch — so
every entry gets a deterministic GUID derived from a stable key:

    guid = sha1("mh::" + deck_slug + "::" + entry_id)

Never derive a GUID from mutable content such as the translation. Treat an
entry's `id` as immutable once shipped: changing it makes the next import create
a new note rather than update the existing one. Rename display fields instead.

Because GUIDs will not match the current collection, importing the rebuilt decks
alongside the old ones produces duplicates. The migration therefore ends with the
owner deleting the old `Modern Hebrew::*` decks — that deletion is theirs to
perform, never automated from here.

## Migration status

**Complete.** The owner backed up the collection, deleted both the legacy
`Modern Hebrew` decks and the staging `Modern Hebrew (rebuild)` tree, and asked for
generated decks to take the real name (2026-09-13). `DEFAULT_DECK_ROOT` is now
`Modern Hebrew`, and generated decks are the only Modern Hebrew decks in the
collection.

That retires the deck-name marker. Two remain, and they are what extraction relies
on to avoid reading its own output back in as source data:

1. **Note type.** Every generated note type is `MHF `-prefixed.
2. **Provenance tag.** Every generated note carries `src::mhf`.

`collection.is_generated()` checks both, and `read_notes()` skips anything matching.
Deck name cannot carry this distinction any more — generated decks sit exactly where
the source decks used to. A re-extraction without that guard would treat derived data
as source and double every deck.

Extraction also refuses to overwrite `data/decks/` without `--force`. It was a
one-time migration; the YAML is the source of truth now.

## Python policy

Conventions follow `berean-bible-bots` (Foundry-derived), scaled to a solo project
without that repo's GitHub App bot infrastructure.

- **Python 3.12** (matches the reference project's CI pin). src-layout under
  `src/hebrew_cards/`.
- **Config lives in `setup.cfg`** — flake8 (`max-line-length = 120`), mypy
  (`disallow_untyped_defs`, `check_untyped_defs`, `ignore_missing_imports`,
  `warn_unused_ignores`), and `[coverage:run] branch = True`.
- **Before every commit**, both must pass clean:
  ```
  python -m flake8 src/ scripts/
  python -m mypy src/ --ignore-missing-imports
  ```
- `requirements.txt` for dependencies — not poetry, not uv.
- `pyproject.toml` is minimal (setuptools build backend + package discovery);
  tool configuration belongs in `setup.cfg`.
- Type hints on every public function. Pydantic models for all YAML-loaded data;
  validation failures are hard errors naming the offending file and entry.
- `per-file-ignores` in `setup.cfg` is the escape hatch for modules holding dense
  aligned Hebrew data literals (the reference project does this for its paradigm
  tables). Use it deliberately, with a comment saying why — never blanket-disable.

## Testing

Adopts the reference project's **Behavioral Verification Principle**: code review is
never sufficient on its own. A capability is not done until it has been observed
producing correct output on a real, known case.

- **Every build capability needs at least one behavioral test** — one that runs the
  real pipeline against real deck data and asserts a known-correct result (an actual
  `.apkg` generated to a temp dir, opened, and inspected). A test that asserts on a
  mock or a synthetic string does not satisfy this.
- Pure-logic unit tests (nikud stripping, transliteration, slug generation) are good
  practice and belong in `tests/unit/`, but do not by themselves meet the bar above.
- Tests needing network access (live TTS) are marked `@pytest.mark.integration` and
  excluded from the default run via `-m "not integration"`. TTS sits behind a provider
  interface with a fake implementation used by the unit suite. **No unit test ever
  makes a network call or spends TTS credit.**
- Coverage uses the **"must not decrease" ratchet**, not a hard minimum: floors live in
  `coverage-baseline.json` and are raised only by `scripts/check_coverage.py
  --update-baseline`, in the same commit that earns the increase. Never hand-edit the
  percentages.
- When reporting that something works, say what was actually run and what the evidence
  was. "Should work" and "the code looks right" are not testing claims.
- **Never quote coverage percentages in a commit message.** `coverage-baseline.json`
  is the record, it is written by the measuring tool, and it is in the same commit.
  A number typed into prose is written before the measurement runs and has been wrong
  every time it has been tried here. If a commit needs to say something about
  coverage, say *why* it moved, not what it is.

## Git workflow

- **Direct pushes to `main` are permitted.** This repo has no branch protection and
  a single contributor, so the reference project's mandatory feature-branch + PR
  workflow is not in force here. Owner decision, 2026-09-13 — revisitable.
- **Feature branches are still the right choice** for anything substantial, risky, or
  worth reviewing as a unit (a migration run, a schema change, anything touching many
  decks at once). Use judgment: small, self-contained, obviously-correct changes go
  straight to `main`; anything the owner would want to read as a coherent diff gets a
  branch.
- **After non-trivial changes: commit and push automatically** — do not ask first.
  This is a standing Phase 2 approval (see the autonomous action policy).
- Never `git add -A` or `git add .` — stage specific paths.
- Commit messages describe the *why*, not just the what.
- GitHub issues are created with `--assignee dnovick`.
- Destructive git operations (`reset --hard`, `clean -f`, `checkout --`) are Phase 1:
  ask first, every time.
- Commits use the default git identity. This project has no author/reviewer bot apps
  configured (unlike the reference project); do not attempt to use one.

## Autonomous action policy

Full trust matrix: **[`docs/policies/autonomous-actions.md`](docs/policies/autonomous-actions.md)**.
Summary of what matters most here:

- **Phase 2 (act, owner reviews after):** writing deck YAML and source files, running
  build/validate/lint scripts, staging and committing on a feature branch, pushing a
  feature branch, creating branches and issues.
- **Phase 1 (ask first):** PR creation and merge, branch deletion, installing new
  packages, anything that spends TTS credit or touches secrets, and **anything that
  writes to the live Anki collection** (which is additionally forbidden outright by
  rule 1 above).

Note that pushing to `main` is a Phase 2 action in this project, unlike the reference
project where branch protection makes it impossible.

## Conventions

- Hebrew is stored in NFC-normalized Unicode, **fully pointed**, in the `hebrew`
  field, and is displayed pointed on cards. A `hebrew_plain` (nikud-stripped) form is
  derived at build time where needed, never stored — the build can strip nikud but
  can never add it, so the source must always carry it.
  An entry whose pointing is uncertain gets `needs_review: true` rather than a guess.
- **No transliteration anywhere.** Hebrew appears as Hebrew script with nikud, on
  every field of every card. This carries over the reference project's language
  standard; see `docs/standards/language.md` for the rationale and the one narrow
  exception. Existing transliterations (the Human Attributes deck's `tov — good`
  style) are dropped during migration, not preserved.
- Deck names in Anki use `Modern Hebrew::<Topic>` and mirror the YAML filename.
- Tags are lowercase, hyphenated, and namespaced: `pos::verb`, `binyan::piel`,
  `topic::kitchen`, `level::intermediate`.
- The existing collection contains corrupted tags leaked from Apple Notes
  (`<MCTag: <x-coredata://...`). Strip these during extraction; never propagate them.

## The review workflow

Edits made in Anki's own editor are destroyed by the next rebuild, because YAML is
the source of truth for content. Rather than forbidding those edits, the project
harvests them on demand.

Entries the extractor could not vouch for carry `needs_review: true` in YAML and a
`needs-review` tag in Anki. The owner reviews them in Anki and records a verdict as a
card flag:

| Flag | Means | Effect on the YAML |
|---|---|---|
| **Green** (`⌘3` on macOS, `Ctrl+3` elsewhere) | correct as it now stands in Anki | adopt any Hebrew or English edit, clear `needs_review` |
| **Red** (`⌘1` / `Ctrl+1`) | still wrong, or edited but unfinished | adopt any edit, keep `needs_review` |
| none | untouched | nothing at all |

`scripts/harvest_review.py` reads the collection (read-only, scratchpad copy), matches
notes to entries by GUID, and applies those verdicts. It reports by default and writes
only with `--apply`.

Rules this depends on:

- **Only an explicit flag may change the source of truth.** An edit on an unflagged
  card is ignored, so a stray keystroke in the browser cannot rewrite the data.
- **A blank field never wipes content.** Far more likely a mistake than an intended
  deletion. Applies to both the Hebrew and the gloss.
- **Both the citation form and the gloss are harvested.** Several entries are flagged
  for a gloss problem rather than a pointing one, so picking up only the Hebrew would
  silently discard the fix.
- Harvest reads *generated* notes — the inverse of extraction, which skips them. Both
  use `collection.is_generated()`, so the two directions cannot overlap.

Anki is still not the source of truth. It is an input to a deliberate, reported,
reviewable harvest, and the YAML remains what builds the decks.

## Audio

**Provider: Google Cloud Text-to-Speech, Chirp 3 HD voices** (he-IL). Owner decision,
2026-09-13.

Chirp 3 HD costs ~$30 per million characters against WaveNet's $16, but at this
project's volume the entire 516-word deck in four voices is ~16.5K characters — under
a dollar either way, and inside the free tier. Cost is small enough that it should
never drive a quality decision here; pick the best-sounding tier available for he-IL.

- API credentials come from the environment (service account JSON path in
  `GOOGLE_APPLICATION_CREDENTIALS`). Never commit a key, never print one, never
  hardcode a project id.
- **Generating audio is a Phase 1 action** — it spends money, however little. Ask
  before a generation run. The cache exists so an approved run is never repeated
  needlessly.
- Audio is content-addressed and cached under `media/` (gitignored). The cache key is
  `sha1(text + voice + speaking_rate)`, so editing an English translation regenerates
  nothing.
- **Voice assignment is deterministic**: each entry gets one voice, chosen by hashing
  its `id` across the available he-IL voice list. The deck as a whole spans every
  voice; an individual card sounds the same on every review. Reshuffling is a seed
  change plus a rebuild, which costs pennies.
- Randomizing the voice per review via template JavaScript was considered and
  rejected for now — better ear training in principle, unreliable on AnkiMobile and
  AnkiDroid in practice. Revisit only if the deterministic split proves insufficient.

## Data model

Full specification: **[`docs/standards/data-model.md`](docs/standards/data-model.md)**

Key rules (always enforced):

- **One note per lexeme**, with per-POS note types (`MHF Noun`, `MHF Adjective`,
  `MHF Verb`, `MHF Root`). The one exception is `MHF Verb Form`, one note per
  conjugated form — each form is independently scheduled, since knowing כּוֹתֶבֶת says
  little about whether you know כָּתַבְתִּי.
- **Store everything, drill a subset.** Full paradigms live in YAML whether or not they
  currently produce cards. A verb's `drill:` list controls which forms become cards;
  the project default is `[present, past.1s, past.3ms]`.
- **Never generate Hebrew forms algorithmically.** Weak verbs break the rules and
  `gizra` only partly predicts how. A script may *propose* regular forms; they land
  with `needs_review: true` and stay flagged until a human confirms.
- **Guard conditional card templates on the field that makes the card meaningful**
  (`{{#Plural}}...{{/Plural}}`), never on one that is always populated — that
  generates junk cards for entries lacking the real content.
- **Fields display, tags select.** Mirror linguistic properties into both.
- `gender` is required on every noun. Unknown gender is `needs_review`, never a guess.
- **Card generation is staged per deck** via `meta.card_types`. Notes are always built
  with full metadata; enabling a card type is a config flip, not a data change. The
  full matrix over the 400 extracted entries is ~1,800 cards — roughly 3.5× the
  current review load — so default new decks to `[audio_meaning]` and let the owner opt in.

## Card design

### Vocabulary

Every entry generates up to two cards. They train different skills and neither
substitutes for the other.

| Card | Front | Back |
|---|---|---|
| **Hebrew → meaning** | the pointed Hebrew | English, plus grammar detail and a replay control when audio exists |
| **Audio → meaning** | audio and nothing else | English, plus the pointed Hebrew |

- **Written Hebrew fronts are permanent, not a stopgap.** The owner wants them.
  Listening is the weaker skill, not the only one being trained.
- **Audio fronts are optional.** They appear for entries that have audio and not
  otherwise — no configuration switch, because Anki builds a card only when its
  front renders non-empty, and the audio front is `{{Audio}}` alone.
- **The audio front must stay audio-only.** Any visible text on it turns a listening
  card into a reading card, and the Hebrew-front card already covers reading.
- Production cards (English → Hebrew) are still not generated. Both card types above
  are recognition; production is a separate skill the owner has not asked for.

Adding audio to a deck therefore doubles its card count. That is the intended
behaviour, but it is worth stating when a deck is about to gain audio.

## Data model

Full specification: **[`docs/standards/data-model.md`](docs/standards/data-model.md)**

Key rules (always enforced):

- **One note per lexeme**, with per-POS note types (`MHF Noun`, `MHF Adjective`,
  `MHF Verb`, `MHF Root`). The one exception is `MHF Verb Form`, one note per
  conjugated form — each form is independently scheduled, since knowing כּוֹתֶבֶת says
  little about whether you know כָּתַבְתִּי.
- **Store everything, drill a subset.** Full paradigms live in YAML whether or not they
  currently produce cards. A verb's `drill:` list controls which forms become cards;
  the project default is `[present, past.1s, past.3ms]`.
- **Never generate Hebrew forms algorithmically.** Weak verbs break the rules and
  `gizra` only partly predicts how. A script may *propose* regular forms; they land
  with `needs_review: true` and stay flagged until a human confirms.
- **Guard conditional card templates on the field that makes the card meaningful**
  (`{{#Plural}}...{{/Plural}}`), never on one that is always populated — that
  generates junk cards for entries lacking the real content.
- **Fields display, tags select.** Mirror linguistic properties into both.
- `gender` is required on every noun. Unknown gender is `needs_review`, never a guess.
- **Card generation is staged per deck** via `meta.card_types`. Notes are always built
  with full metadata; enabling a card type is a config flip, not a data change. The
  full matrix over the 400 extracted entries is ~1,800 cards — roughly 3.5× the
  current review load — so default new decks to `[audio_meaning]` and let the owner opt in.

## Card design

### Vocabulary (the primary card type)

One card per entry. No reverse card.

| Side | Content |
|---|---|
| **Front** | Audio only. No Hebrew text, no English, no hint. |
| **Back** | English translation, plus the pointed Hebrew, plus a replay control. |

The front must contain **nothing but the audio**. Any visible text turns a listening
exercise into a reading exercise, which is the failure mode this whole project exists
to avoid. This is the owner's explicit design (2026-09-13), not an inference.

The Hebrew on the back is answer content, not a second card — the answer is already
committed by the time it is visible, so it cannot short-circuit the exercise, and it
reinforces spelling and nikud at no extra review cost.

Production cards (English → Hebrew) are **not** generated. The owner's gap is
recognition, not production.

