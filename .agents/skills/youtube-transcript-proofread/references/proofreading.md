# Agent Proofreading Rules

## Evidence hierarchy

Use evidence in this order:

1. repeated, clear occurrences in the audio transcript;
2. source-linked slides, proposal, issue, repository identifiers, or official glossary;
3. domain context that admits only one plausible term;
4. phonetic inference.

Only levels 1-3 justify an unmarked correction. Mark level 4 as uncertain.

## Allowed corrections

- punctuation, spacing, capitalization, and obvious filler cleanup;
- stable product, API, type, field, command, and person-provided terminology;
- obvious homophones where the technical context is decisive;
- ASR segmentation that splits one sentence across adjacent cues;
- removal of text proven to extend past the media duration.

## Disallowed transformations

- turning a paraphrase into quotation marks;
- filling inaudible speech from expected proposal text;
- changing a weak statement into agreement, approval, or consensus;
- assigning a real name from voice, speaking style, or presumed meeting role;
- silently deleting disagreement, uncertainty, false starts, or corrections that matter;
- treating Kubernetes `Ready` as business serving readiness unless the speaker says so.

## Uncertainty notation

- `[unclear]`: speech cannot be recovered reliably.
- `[uncertain: PDB]`: one plausible candidate exists but is not proven.
- `[audio gap HH:MM:SS-HH:MM:SS]`: missing or unusable audio.
- `[clip ends mid-sentence]`: requested range ends before the utterance.

Do not emit several speculative candidates unless they materially affect meaning.

## Speaker labels

Without diarization, identify turns only by neutral editorial role:

- `Presenter`
- `Question`
- `Response`
- `Participant A/B` when roles are not clear

Add one sentence stating that labels are editorial and are not identity attribution. Use a real name only when the recording, official transcript, or visible meeting artifact explicitly establishes it.

## Corrected transcript format

```markdown
# <Title> - Proofread Transcript

Source: <URL>
Duration: `HH:MM:SS`
Coverage: `HH:MM:SS-HH:MM:SS`
Method: `<model>`, `<device>/<compute type>`, language `<code>`

## Reliability

- Subtitle availability:
- Conditioning and glossary:
- Speaker limitation:
- Excluded or rerun ranges:

## Time Index

| Time | Topic |
| --- | --- |

## Corrected Transcript

### `HH:MM:SS-HH:MM:SS` - <topic>

Presenter: ...

Question: ...

## Corrections

| Raw ASR | Corrected | Evidence |
| --- | --- | --- |

## Evidence Boundaries

- Proves:
- Does not prove:
```

## Review checklist

- Compare the first and last timestamps with source duration.
- Recheck every long silence, repeated phrase, and final segment.
- Verify all domain identifiers against primary sources.
- Preserve negation, modality, and qualifiers such as “initial thought,” “maybe,” and “not sure.”
- Keep examples distinct from defaults and guarantees.
- Distinguish a question, suggestion, tentative direction, and accepted decision.
- Link the raw SRT and manifest so corrections remain auditable.
