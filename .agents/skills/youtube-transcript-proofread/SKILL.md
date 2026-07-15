---
name: youtube-transcript-proofread
description: Transcribe YouTube videos locally with open-source Whisper models, then produce an agent-proofread timestamped transcript with terminology correction, hallucination checks, coverage disclosure, and evidence boundaries. Use when the user asks to turn a YouTube video or meeting recording into text, subtitles, SRT, a cleaned transcript, meeting evidence, or a domain-corrected transcript, especially when YouTube captions are absent or unreliable.
---

# YouTube Transcript Proofread

Create two distinct artifacts:

1. a reproducible, timestamped ASR transcript from a local open-source model;
2. an Agent-proofread transcript that corrects supported terms without inventing speech.

Never describe a partial clip as the full video transcript.

## Workflow

### 1. Confirm source and scope

Inspect every URL before downloading:

```powershell
python -m yt_dlp --print "%(id)s`n%(title)s`n%(duration_string)s`n%(duration)s" --no-download "<URL>"
```

Report the exact title and duration. Keep video IDs separate when the user supplies multiple links. Ask about scope only if the requested coverage cannot be inferred; otherwise transcribe the full video. For a clip, record both the absolute video timestamps and the clip duration.

Check subtitle availability. Prefer an official human transcript when the user only needs the published wording. Use this skill when captions are missing, unreliable, or the user explicitly wants local open-source transcription.

### 2. Prepare the local runtime

Use a dedicated Python environment with `yt-dlp` and `faster-whisper`. Read [references/setup.md](references/setup.md) only when dependencies, GPU support, model selection, or installation need attention.

Before downloading a model, tell the user the approximate one-time cost. Prefer a local `large-v3-turbo` model for Chinese/English technical meetings. Use CPU `int8` only when CUDA is unavailable.

Do not upload audio to a cloud API unless the user explicitly requests and authorizes it. Do not silently import browser cookies.

### 3. Generate the raw transcript

Run the bundled script:

```powershell
python "<skill-path>/scripts/transcribe_youtube.py" "<URL>" `
  --output "<output-dir>" `
  --model "large-v3-turbo" `
  --language zh `
  --glossary "<optional-terms.txt>"
```

For an already downloaded file, pass the local audio path. Preserve provenance with `--source-url`, `--title`, `--video-id`, `--channel`, and `--duration`. For a bounded video range, use `--clip HH:MM:SS-HH:MM:SS`; output timestamps remain absolute to the source media.

The default disables previous-text conditioning. This reduces long-context and silence hallucinations; domain continuity comes from the glossary and the Agent review. The script writes:

- `<id>.raw.srt`
- `<id>.raw.txt`
- `<id>.segments.json`
- `<id>.manifest.json`
- downloaded audio under `audio/` for URL inputs

### 4. Validate before proofreading

Run:

```powershell
python "<skill-path>/scripts/validate_srt.py" "<id>.raw.srt" --manifest "<id>.manifest.json"
```

Treat these as blocking until investigated:

- timestamps outside the source duration;
- non-monotonic or malformed cues;
- a generated tail beyond the real audio;
- repeated phrases across silence;
- a long final cue inconsistent with the remaining duration.

If only one range is suspect, rerun that absolute range with a stronger glossary and `--no-condition-on-previous-text`. Do not discard questionable content silently; record what was excluded and why.

### 5. Build review chunks

For long recordings, create deterministic 10-20 minute packets:

```powershell
python "<skill-path>/scripts/make_review_chunks.py" "<id>.raw.srt" `
  --output "<output-dir>/review" `
  --minutes 15 `
  --title "<video title>" `
  --source-url "<URL>"
```

Use subagents only for independent, bounded chunks. Give them the raw chunk and proofreading rules, not expected conclusions. The primary Agent must reconcile terminology and evidence boundaries across all chunks.

### 6. Agent-proofread

Read [references/proofreading.md](references/proofreading.md) before editing or summarizing the transcript.

Keep three layers separate:

- **Raw ASR**: model output, unchanged.
- **Corrected transcript**: punctuation and high-confidence word/term corrections while preserving speech and timestamps.
- **Meeting digest or analysis**: clearly labeled paraphrase; never present it as verbatim transcript.

Use repository source, proposal text, slides, issue terminology, and repeated audio context to support corrections. Mark uncertain words as `[unclear]` or `[uncertain: candidate]`. Never infer named speakers from voice alone. Without diarization, use neutral roles such as `Presenter`, `Question`, or `Response`, and state that the labels are editorial.

### 7. Deliver and record provenance

Deliver the raw SRT/TXT plus a readable proofread Markdown file. Include:

- source URL, title, exact duration, and covered range;
- model, device, language, prompt/glossary, and conditioning setting;
- subtitle availability;
- corrections and excluded hallucinations;
- speaker-attribution limitation;
- what the recording proves and does not prove when used as engineering evidence.

For project work, place reusable prose in the project's report directory and keep large audio/model/cache artifacts in ignored temporary storage. Do not commit copyrighted audio unless the user explicitly requests it and has the right to do so.

## Completion Gate

Do not call the work complete until:

- source duration and transcript coverage match the claim;
- `validate_srt.py` passes or every exception is documented;
- raw ASR remains available for audit;
- the proofread output distinguishes corrections from paraphrase;
- local file links and timestamps have been checked;
- no named speaker attribution or community consensus was invented.
