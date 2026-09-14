---
type: policy
scope: modern-hebrew-flashcards
status: draft
created: 2026-09-14
version: "0.1"
foundry-ref: "Operating Agreement F-1.7 §5 (Quality Standards) — Behavioral Verification Principle"
---

# Test Coverage Policy

Adapted from `berean-bible-bots`. Coverage is governed by a **must-not-decrease
ratchet** rather than a fixed minimum: every change leaves coverage at or above where
it found it, so the number climbs as a side effect of ordinary work instead of
requiring a separate campaign.

## Two measurement modes

| Mode | Command | Measures | Enforced |
|---|---|---|---|
| **unit** | `python scripts/check_coverage.py` | `pytest -m "not integration"` | CI, blocking |
| **full** | `python scripts/check_coverage.py --full` | the whole suite | local only |

Integration tests need the owner's Anki collection, which CI never has. They skip
rather than fail when it is absent, so a CI run measures strictly less than a local
one — hence the two floors in `coverage-baseline.json`.

## Measuring the unit floor

**Measure `unit_min_percent` in an environment matching CI's install list** — the
`pip install` line in `.github/workflows/ci.yml`, on Python 3.12. A local environment
with extra packages, or a different interpreter, measures a number CI can never reach,
and the next PR fails the ratchet with no code change of its own.

`full_min_percent` is never CI-enforced and should be measured in the normal dev
environment.

## Lowering a floor

`--update-baseline` **refuses** to lower a floor without `--reason`, which it records
in the baseline file. This is enforced in the tool rather than left to discipline:
the rule was breached three times in a single day before that guard existed, twice
while writing a commit about having breached it.

A drop is sometimes legitimate — new CLI code in a feature, or statements only
reachable by integration tests. Say which.

Never hand-edit the percentages. The 0.1-point tolerance only makes sense against a
number the tool actually measured.

## Scope

Tracks `src/hebrew_cards/` and `scripts/`. Both are measured, including the CLI entry
points — most new code in a feature lands in its script, and exempting them is how the
floor quietly slid for several commits.

## Behavioral tests

Per the Behavioral Verification Principle, coverage is not the bar for "done". A
capability must be observed producing correct output on real data — a real `.apkg`
built and inspected, the real collection read. Those tests are marked `integration`
and are the reason the full floor exists separately.
