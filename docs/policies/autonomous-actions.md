---
type: policy
scope: modern-hebrew-flashcards
status: draft
created: 2026-09-13
version: "0.1"
foundry-ref: "Operating Agreement F-1.7 §6 (Progressive Autonomy) + §3 (Decision Authority)"
---

# Autonomous Action Policies

The per-domain trust matrix for this project, following the model established in
`berean-bible-bots`. It defines which action categories operate at Phase 1, 2, or 3,
and the criteria for promotion between them.

**Status: draft.** Phase assignments start conservative because this project is new
and has no execution history yet. Domains are promoted as reliability is demonstrated,
not assumed up front.

---

## Phase Definitions

| Phase | Model | Gate |
|---|---|---|
| **1** | Present → owner approves → act | Default for all new action types |
| **2** | Act → post-hoc owner review | Promoted after demonstrated reliability |
| **3** | Full autonomy; no review required | Not granted to any domain |

**Promotion criteria (all three required):**
1. ~5 successful executions at the current phase with no incidents
2. Explicit owner request to promote
3. A rollback or audit mechanism exists for the domain

**Demotion:** any domain may be demoted to Phase 1 after an incident, at the owner's
discretion.

---

## Domain Trust Matrix

| # | Domain | Phase | Scope | Restrictions |
|---|---|---|---|---|
| 1 | **Deck data writes** | 2 | Creating and editing `data/decks/*.yaml` during an assigned task | Owner reviews via `git diff` before merge. Hebrew content follows the accuracy rule — flag uncertainty with `needs_review: true` rather than guessing |
| 2 | **Source code writes** | 2 | `src/hebrew_cards/`, `scripts/`, `tests/` | flake8 + mypy must pass before commit |
| 3 | **Script execution** | 2 | Build, validate, and lint scripts run as part of the assigned task | Scripts that spend money (TTS) or write to Anki are separate domains below |
| 4 | **Git staging + commit** | 2 | `git add <specific paths>`, `git commit` on the current feature branch | Never `git add -A` / `git add .`. Destructive ops (`reset --hard`, `clean -f`, `checkout --`) are Phase 1. Message must describe the *why* |
| 5 | **Git push** | 2 | `git push` to `main` or to a feature branch | No branch protection is configured and there is one contributor. Substantial or reviewable-as-a-unit work should still use a branch — see the note below |
| 6 | **Branch creation** | 2 | `git checkout -b` + `git push -u` | Deleting branches is Phase 1 |
| 7 | **GitHub — issue creation** | 2 | `gh issue create --assignee dnovick` | Body must accurately describe the work |
| 8 | **GitHub — PR creation** | 1 | `gh pr create` | Owner asks; Claude creates and reports back. PRs are optional here, not the mandatory path |
| 9 | **GitHub — PR merge** | 1 | `gh pr merge` | Owner requests explicitly |
| 10 | **TTS generation (paid API)** | 1 | Any call to a cloud TTS provider | Costs money per character. Owner approves a generation run; the media cache exists so an approved run is never repeated needlessly |
| 11 | **Reading the Anki collection** | 2 | Copying `collection.anki2` to scratchpad and querying the copy read-only | `Modern Hebrew::*` only. Never open the live file directly |
| 12 | **Writing to the Anki collection** | — | — | **Forbidden.** Not a Phase 1 action, not promotable. Output is `.apkg` files the owner imports by hand |

---

## On pushing to `main`

The reference project forbids this absolutely, enforced by branch protection. **This
project permits it** (owner decision, 2026-09-13): the repo has no protection
configured and a single contributor, so a mandatory PR round-trip would be ceremony
without a reviewer.

This is a deliberate, revisitable relaxation rather than an oversight. If branch
protection is ever enabled here, this domain reverts to the reference project's rule
and this section should be deleted.

The underlying discipline does not change: commits are still scoped to specific paths,
still explain *why*, and work worth reading as a coherent diff still belongs on a
branch.

---

## Actions That Are Always Phase 1

Regardless of future promotions:

- Merging a PR
- Deleting branches, tags, or releases
- Any action affecting billing, secrets, or repository access
- Installing new Python packages
- Spending TTS credit

---

## Project-Specific Prohibitions

Beyond the phase matrix, these are absolute:

- **Never modify the live Anki collection.** Read-only, via a scratchpad copy.
- **Never touch non-Modern-Hebrew decks.** `BBH::*`, `BBG::*`, `Biblical Hebrew::*`,
  and `Psalm 119::*` belong to a separate area of study and are out of scope for
  every operation, including read-only extraction.
- **Never delete an Anki deck.** Deck deletion during migration is the owner's
  action, performed by hand in the Anki UI.

---

## Review Cadence

- **Per-session:** Claude surfaces Phase-1 actions and waits for explicit approval.
- **Per-PR:** Owner reviews the diff before merge.
- **Policy review:** revisit when a new action type is introduced, after any incident,
  or when this project's Foundry alignment reaches a checkpoint (at which point this
  document moves from `status: draft` to `status: active`).
