---
type: standard
scope: modern-hebrew-flashcards
status: draft
created: 2026-09-13
version: "0.1"
---

# Data Model

How deck source data is structured, and how it maps onto Anki note types and cards.

## Principles

1. **One note per lexeme**, not per card. A word is one thing; the several cards that
   drill it are views of that thing. This gives Anki sibling burying for free — you
   won't see the same word five times in one session.
   *Exception:* verb forms, which get their own notes (see below).
2. **Per-POS note types**, not one universal type. Nouns, adjectives, and verbs have
   genuinely different shapes; a union type would leave most fields empty on most notes.
3. **Store everything, drill a subset.** Storage is free; review time is not. Full
   paradigms live in YAML whether or not they currently generate cards.
4. **Fields display, tags select.** If it appears on a card, it's a field. If it only
   picks cards out of a pile, it's a tag. Linguistic properties are usually both.
5. **Over-provision fields.** An empty Anki field costs nothing. Adding a field to a
   note type already in use forces a full AnkiWeb re-upload when syncing across
   devices, so design generously up front.

## Conditional card generation

Anki creates a card only if its template's **front side renders non-empty**. This is
the mechanism the whole model relies on: a noun with no recorded plural simply does not
get a plural card, with no empty-card cleanup needed.

Template fronts must therefore be guarded on the field that makes the card meaningful:

```
{{#Plural}}{{PluralAudio}}{{/Plural}}
```

Never guard on a field that is always populated — that generates junk cards for
entries lacking the real content.

## Schemas

### Noun

```yaml
- id: kadur
  pos: noun
  hebrew: כָּדוּר
  english: ball
  gender: m              # m | f  — required; governs all agreement
  plural: כַּדּוּרִים        # optional; omit if genuinely uncountable
  plural_gender: m       # optional; only when it differs from `gender`
  construct: כַּדּוּר       # optional
  tags: [topic::sport]
```

`gender` is **required** on every noun. Hebrew gender is frequently not inferable from
the sound of the word, and every adjective and verb that agrees with it depends on
knowing it. An unknown gender is `needs_review: true`, never a guess.

### Adjective

```yaml
- id: gadol
  pos: adjective
  english: big, large
  forms:
    ms: גָּדוֹל           # citation form
    fs: גְּדוֹלָה
    mp: גְּדוֹלִים
    fp: גְּדוֹלוֹת
```

All four agreement forms are stored. `forms.ms` doubles as the citation form; there is
no separate `hebrew` key for adjectives.

### Verb

```yaml
- id: katav
  pos: verb
  lemma: כָּתַב            # 3ms past — the citation form
  root: כ־ת־ב
  binyan: paal           # paal | niphal | piel | pual | hiphil | hophal | hitpael
  gizra: shlemim         # weak-verb class; governs the conjugation pattern
  english: write
  infinitive: לִכְתּוֹב
  present: {ms: כּוֹתֵב, fs: כּוֹתֶבֶת, mp: כּוֹתְבִים, fp: כּוֹתְבוֹת}
  past:    {1s: כָּתַבְתִּי, 2ms: כָּתַבְתָּ, 3ms: כָּתַב, ...}
  future:  {...}
  imperative: {ms: כְּתוֹב, ...}
  drill: [present, past.1s, past.3ms]
```

**`drill:` is the review-load control.** It lists which stored forms become cards.
Everything else stays available for reference and for later promotion. The project
default is `[present, past.1s, past.3ms]` — six form cards per verb, covering what is
heard constantly in speech without letting morphology dominate the deck.

Changing what you drill is a one-line edit plus a rebuild, never a re-authoring job.

### Never generate Hebrew forms algorithmically

Conjugation looks derivable from root + binyan. It is not: weak verbs break the rules
constantly, and `gizra` only partly predicts how. A script may **propose** regular
forms, but they enter YAML with `needs_review: true` and stay flagged until a human
confirms them. This is hard rule 5 of `CLAUDE.md` applied to morphology.

## Note types

| Note type | One note per | Key fields |
|---|---|---|
| `MHF Noun` | lexeme | Hebrew, English, Gender, Plural, Audio, PluralAudio |
| `MHF Adjective` | lexeme | FormMS, FormFS, FormMP, FormFP, English, Audio* |
| `MHF Verb` | lexeme | Lemma, English, Root, Binyan, Gizra, Infinitive, Audio |
| `MHF Verb Form` | **form** | Form, Lemma, Root, Binyan, Tense, Person, Number, Gender, Audio |
| `MHF Root` | root | Root, Members (words in the decks sharing it) |

`MHF Verb Form` is the deliberate exception to one-note-per-lexeme. Each conjugated
form is its own note because each is independently scheduled — knowing כּוֹתֶבֶת says
little about whether you know כָּתַבְתִּי. Form notes are generated from the parent
verb's `drill:` list, so one YAML entry feeds both the meaning card and the morphology
cards.

## Card matrix

| Card | Front | Back | From |
|---|---|---|---|
| Audio → meaning | audio only | English + pointed Hebrew | every entry |
| Gender ID | noun audio | m / f | `MHF Noun` |
| Plural production | singular audio | plural form | `MHF Noun`, guarded on `Plural` |
| Adjective agreement | citation + target gender/number | agreeing form | `MHF Adjective` |
| Form → parse | conjugated-form audio | person, number, tense, binyan, lemma | `MHF Verb Form` |
| Root family | the root | words in the decks derived from it | `MHF Root` |

The front of an audio card contains **nothing but audio** — see `CLAUDE.md`, Card design.

## Staged generation

The full matrix over the 400 extracted entries produces roughly 1,800 cards — about
3.5× the current review load, with verb forms alone accounting for over half of it.

Card generation is therefore **staged**, controlled per deck:

```yaml
# data/decks/nouns.yaml
meta:
  card_types: [audio_meaning]          # start here
  # card_types: [audio_meaning, gender_id, plural_production]   # enable when ready
```

Every note is built with its full metadata regardless. Turning a card type on is a
config change and a rebuild — the data never needs revisiting. Start each deck at
`audio_meaning` and add types as review load allows.

## Tags

Key fields are mirrored as tags so cards can be selected without a rebuild:

`pos::noun` · `gender::f` · `binyan::piel` · `gizra::pe-nun` · `topic::kitchen` ·
`level::intermediate` · `src::mhf`

This is what makes Anki filtered decks useful — "drill every piel verb" or "every
feminine noun I've failed twice" becomes a browser search against tags already present.

Authoring metadata (`needs_review`, source provenance, notes-to-self) stays in YAML and
is **not** mirrored into Anki, with one exception: `needs_review: true` also emits a
`needs-review` tag, so flagged entries are findable in the browser.
