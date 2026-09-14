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

## Migration and deck separation

The rebuilt notes will not match the existing ones, so both sets can coexist in
the collection. Three independent markers keep them distinguishable, so the owner
never has to identify cards by eye:

1. **Deck root.** Migration builds target `Modern Hebrew (rebuild)::<Topic>`, not
   `Modern Hebrew::<Topic>`. The deck root is configurable, never hardcoded.
2. **Note types.** Every generated note type is named with an `MHF ` prefix
   (`MHF Vocab`, `MHF Listening`, `MHF Cloze`). Every legacy note is `Basic`,
   `Basic_2_fields`, or `Basic (and reversed card)`. Search `note:MHF*` partitions
   them regardless of deck.
3. **Provenance tag.** Every generated note carries `src::mhf`. Nothing else in the
   collection has it.

Documented procedure, in order:

1. Export the current `Modern Hebrew::*` decks to `archive/modern-hebrew-<date>.apkg`
   so the deletion is reversible. Do this before anything else.
2. Build and import under the `Modern Hebrew (rebuild)` root.
3. Owner reviews the new decks against the old.
4. **Owner** deletes the `Modern Hebrew` tree and renames `Modern Hebrew (rebuild)`
   to `Modern Hebrew`. Both steps happen in the Anki UI, by hand. Never automate
   deck deletion from this project.
5. Flip the configured deck root back to `Modern Hebrew` for subsequent builds.

Until step 5 is done, do not build to the `Modern Hebrew` root — a build that
lands in the live tree destroys the separation the whole procedure depends on.

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

## Git workflow

- **All changes go on a feature branch + PR.** Never push directly to `main`.
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

## Conventions

- Hebrew is stored in NFC-normalized Unicode, with nikud, in the `hebrew` field.
  A `hebrew_plain` (nikud-stripped) form is derived at build time, never stored.
- Transliteration is generated, not hand-written, and follows a single documented
  scheme (see `docs/transliteration.md` when it exists).
- Deck names in Anki use `Modern Hebrew::<Topic>` and mirror the YAML filename.
- Tags are lowercase, hyphenated, and namespaced: `pos::verb`, `binyan::piel`,
  `topic::kitchen`, `level::intermediate`.
- The existing collection contains corrupted tags leaked from Apple Notes
  (`<MCTag: <x-coredata://...`). Strip these during extraction; never propagate them.

## Audio

- Target is a cloud multi-voice Hebrew TTS (Google Cloud or Azure). Voice variety
  is the point — a single voice trains a brittle ear.
- Audio is content-addressed and cached under `media/` (gitignored). The cache key
  includes text, voice, and speed, so regenerating a deck does not re-bill unchanged
  cards.
- API keys come from the environment. Never commit a key, never print one.
- Every listening card gets at least two voices across its variants where the card
  type allows it.
