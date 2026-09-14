---
type: standard
scope: modern-hebrew-flashcards
status: draft
created: 2026-09-13
version: "0.1"
---

# Language and Display Standards

Adapted from `berean-bible-bots`' language standard. Where this project departs, the
departure is stated and justified.

## No transliteration

**Hebrew appears as Hebrew script, with nikud, on every field of every card.** No
romanization anywhere — not on prompts, not on answers, not in hint fields.

This carries over the reference project's rule unchanged. The original rationale is
that transliteration lets a learner dodge the script entirely, and the habit is hard
to unlearn once formed.

A second rationale applies specifically here. Transliteration's main remaining value
for Modern Hebrew is marking stress, which nikud does not encode — `אוֹכֶל` is *ókhel*
(food) or *okhél* (eating) depending on it. But in this project every card carries
audio, and **the recording is the stress cue**. A written stress mark would be a
redundant second signal, and a weaker one, since the goal is training the ear rather
than the eye.

**The one narrow exception**, inherited from the reference standard: a brief
illustrative English sound-alike is permitted when a card is specifically teaching a
pronunciation concept (e.g. explaining that ח and כ differ from ה). This is a
pronunciation aid tied to a single teaching point — not a systematic transliteration
column, and never a field on a vocabulary card.

Existing transliterations in the collection are **dropped** during migration, not
carried forward.

## Nikud

- Source YAML always stores **fully pointed** Hebrew. The build can strip nikud; it
  can never add it. Incomplete pointing in the source is a data defect.
- Cards **display** the pointed form.
- `hebrew_plain` is derived at build time where an unpointed form is needed. It is
  never stored in the source.
- Where an entry's correct pointing is uncertain, mark it `needs_review: true`.
  Never guess. A confidently wrong nikud is worse than a flagged gap.

## Text handling

- Hebrew is stored NFC-normalized. Normalize on load, not on write, so
  externally-edited files are handled consistently.
- Final letter forms (ך ם ן ף ץ) are stored as written. Never algorithmically
  substitute final forms — Hebrew source data is authored correctly or flagged.
- Any HTML template rendering Hebrew sets `direction: rtl; unicode-bidi: embed` on
  the containing element. Never mix a Hebrew string and a Latin-script label on the
  same line without an explicit direction wrapper — bidi reordering renders it
  backwards, a bug the reference project hit repeatedly.

## Tables and output

- GitHub-Flavored Markdown for all documentation tables — never ASCII art or pasted
  terminal output.
