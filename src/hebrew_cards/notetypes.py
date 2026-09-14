"""Anki note types for generated decks.

One note type per part of speech, named with an `MHF ` prefix so generated notes are
distinguishable from the legacy `Basic`/`Basic_2_fields` ones at a glance and by
search — see docs/policies/autonomous-actions.md on migration separation.

Fields are deliberately over-provisioned: an empty Anki field costs nothing, while
adding a field to a note type already in use forces a full AnkiWeb re-upload.
"""

from __future__ import annotations

import genanki

from .ids import stable_id

CSS = """
.card {
  font-family: -apple-system, "Helvetica Neue", sans-serif;
  font-size: 22px;
  text-align: center;
  color: #1a1a1a;
  background: #fdfdfd;
}
.heb {
  font-family: "Taamey Frank CLM", "SBL Hebrew", "Times New Roman", serif;
  font-size: 44px;
  direction: rtl;
  unicode-bidi: embed;
  line-height: 1.6;
}
.english { font-size: 26px; margin-top: 12px; }
.meta { font-size: 16px; color: #666; margin-top: 14px; direction: rtl; unicode-bidi: embed; }
.placeholder {
  font-size: 14px;
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-radius: 6px;
  padding: 6px 10px;
  margin-bottom: 18px;
  direction: ltr;
}
hr#answer { margin: 22px 0; border: none; border-top: 1px solid #ddd; }
"""

# Until milestone 3 generates audio, the Audio field is empty on every note. A strict
# audio-only front would render blank, so Anki would generate no card at all and the
# deck would be unreviewable. This falls back to the written form, clearly marked, and
# switches to audio by itself the moment the field is populated.
_NO_AUDIO_NOTICE = '<div class="placeholder">no audio yet — reading, not listening</div>'


def _audio_front(citation_field: str) -> str:
    return (
        "{{#Audio}}{{Audio}}{{/Audio}}\n"
        "{{^Audio}}" + _NO_AUDIO_NOTICE
        + f'<div class="heb">{{{{{citation_field}}}}}</div>{{{{/Audio}}}}'
    )


def _audio_back(citation_field: str, meta_rows: str = "") -> str:
    return (
        "{{FrontSide}}\n<hr id=answer>\n"
        '<div class="english">{{English}}</div>\n'
        f'<div class="heb">{{{{{citation_field}}}}}</div>\n'
        + meta_rows
    )


def _model(name: str, fields: list[str], templates: list[dict[str, str]]) -> genanki.Model:
    return genanki.Model(
        model_id=stable_id(name),
        name=name,
        fields=[{"name": f} for f in fields],
        templates=templates,
        css=CSS,
    )


def noun_model() -> genanki.Model:
    return _model(
        "MHF Noun",
        ["Hebrew", "English", "Gender", "Plural", "Audio", "PluralAudio", "Notes"],
        [
            {
                "name": "Audio → meaning",
                "qfmt": _audio_front("Hebrew"),
                "afmt": _audio_back(
                    "Hebrew",
                    '{{#Gender}}<div class="meta">{{Gender}}</div>{{/Gender}}\n'
                    '{{#Plural}}<div class="meta">{{Plural}}</div>{{/Plural}}',
                ),
            }
        ],
    )


def adjective_model() -> genanki.Model:
    return _model(
        "MHF Adjective",
        ["Hebrew", "English", "FormMS", "FormFS", "FormMP", "FormFP", "Audio", "Notes"],
        [
            {
                "name": "Audio → meaning",
                "qfmt": _audio_front("Hebrew"),
                "afmt": _audio_back(
                    "Hebrew",
                    '{{#FormFS}}<div class="meta">{{FormFS}}</div>{{/FormFS}}',
                ),
            }
        ],
    )


def verb_model() -> genanki.Model:
    return _model(
        "MHF Verb",
        ["Lemma", "English", "Root", "Binyan", "Gizra", "Infinitive", "Audio", "Notes"],
        [
            {
                "name": "Audio → meaning",
                "qfmt": _audio_front("Lemma"),
                "afmt": _audio_back(
                    "Lemma",
                    '{{#Infinitive}}<div class="meta">{{Infinitive}}</div>{{/Infinitive}}\n'
                    '{{#Binyan}}<div class="meta">{{Binyan}}</div>{{/Binyan}}',
                ),
            }
        ],
    )


def particle_model() -> genanki.Model:
    """Adverbs, prepositions, and modals — no inflection worth modelling yet."""
    return _model(
        "MHF Particle",
        ["Hebrew", "English", "Audio", "Notes"],
        [
            {
                "name": "Audio → meaning",
                "qfmt": _audio_front("Hebrew"),
                "afmt": _audio_back("Hebrew"),
            }
        ],
    )


MODELS_BY_POS = {
    "noun": noun_model,
    "adjective": adjective_model,
    "verb": verb_model,
    "adverb": particle_model,
    "preposition": particle_model,
    "modal": particle_model,
    "unknown": particle_model,
}


def model_for(pos: str) -> genanki.Model:
    """Return the note type for `pos`."""
    try:
        return MODELS_BY_POS[pos]()
    except KeyError:
        raise ValueError(f"no note type for part of speech {pos!r}") from None
