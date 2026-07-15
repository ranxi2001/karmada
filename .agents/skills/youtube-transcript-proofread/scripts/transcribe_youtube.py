#!/usr/bin/env python3
"""Download YouTube audio or reuse a local file and transcribe it with faster-whisper."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def find_yt_dlp() -> str:
    names = ["yt-dlp.exe", "yt-dlp"] if sys.platform == "win32" else ["yt-dlp"]
    for name in names:
        found = shutil.which(name)
        if found:
            return found
        beside_python = Path(sys.executable).with_name(name)
        if beside_python.exists():
            return str(beside_python)
    raise RuntimeError("yt-dlp is not installed or discoverable")


def run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "command failed")
    return json.loads(result.stdout)


def inspect_youtube(yt_dlp: str, url: str) -> dict[str, Any]:
    data = run_json([yt_dlp, "--dump-single-json", "--no-download", "--no-playlist", url])
    return {
        "input": url,
        "url": data.get("webpage_url") or url,
        "video_id": data.get("id"),
        "title": data.get("title"),
        "duration_seconds": data.get("duration"),
        "duration_string": data.get("duration_string"),
        "channel": data.get("channel"),
        "upload_date": data.get("upload_date"),
        "manual_subtitle_languages": sorted((data.get("subtitles") or {}).keys()),
        "automatic_caption_languages": sorted((data.get("automatic_captions") or {}).keys()),
    }


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return cleaned or "transcript"


def find_existing_audio(audio_dir: Path, video_id: str) -> Path | None:
    matches = sorted(
        path
        for path in audio_dir.glob(f"{video_id}.*")
        if path.is_file() and path.suffix.lower() not in {".json", ".part", ".ytdl"}
    )
    return matches[0] if matches else None


def download_audio(yt_dlp: str, url: str, audio_dir: Path, video_id: str) -> Path:
    audio_dir.mkdir(parents=True, exist_ok=True)
    output = audio_dir / f"{video_id}.%(ext)s"
    result = subprocess.run(
        [
            yt_dlp,
            "-f",
            "bestaudio[ext=m4a]/bestaudio",
            "--no-playlist",
            "--quiet",
            "--print",
            "after_move:filepath",
            "-o",
            str(output),
            url,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "yt-dlp audio download failed")
    paths = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    if paths and paths[-1].exists():
        return paths[-1]
    existing = find_existing_audio(audio_dir, video_id)
    if existing:
        return existing
    raise RuntimeError("yt-dlp completed but the audio file could not be located")


def parse_clock(value: str) -> float:
    value = value.strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        return float(value)
    parts = value.split(":")
    if len(parts) not in {2, 3}:
        raise argparse.ArgumentTypeError(f"invalid time: {value}")
    try:
        numbers = [float(part) for part in parts]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid time: {value}") from exc
    if len(numbers) == 2:
        return numbers[0] * 60 + numbers[1]
    return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]


def parse_clip(value: str) -> tuple[float, float]:
    try:
        start_text, end_text = value.split("-", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("clip must be START-END") from exc
    start = parse_clock(start_text)
    end = parse_clock(end_text)
    if start < 0 or end <= start:
        raise argparse.ArgumentTypeError("clip end must be greater than start")
    return start, end


def format_srt_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def read_glossary(path: Path | None) -> list[str]:
    if path is None:
        return []
    values = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        term = line.strip()
        if term and not term.startswith("#"):
            values.append(term)
    return values


def choose_device(requested: str) -> str:
    if requested != "auto":
        return requested
    import ctranslate2

    return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="YouTube URL or local audio/video file")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="large-v3-turbo")
    parser.add_argument("--language")
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--compute-type", default="auto")
    parser.add_argument("--glossary", type=Path)
    parser.add_argument("--prompt", default="")
    parser.add_argument("--clip", type=parse_clip)
    parser.add_argument("--duration", type=float, help="Duration override for a local file")
    parser.add_argument("--source-url", help="Original URL when transcribing a local file")
    parser.add_argument("--title", help="Source title override for a local file")
    parser.add_argument("--video-id", help="Source video ID override for a local file")
    parser.add_argument("--channel", help="Source channel override for a local file")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument(
        "--condition-on-previous-text",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument("--reuse-audio", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    is_url = args.source.startswith(("https://", "http://"))
    yt_dlp = find_yt_dlp() if is_url else ""
    if is_url:
        source = inspect_youtube(yt_dlp, args.source)
        video_id = safe_id(str(source.get("video_id") or "youtube"))
        audio_dir = args.output / "audio"
        audio_path = find_existing_audio(audio_dir, video_id) if args.reuse_audio else None
        if audio_path is None:
            print(f"Downloading audio for {source.get('title')} ({source.get('duration_string')})")
            audio_path = download_audio(yt_dlp, args.source, audio_dir, video_id)
    else:
        audio_path = Path(args.source).expanduser().resolve()
        if not audio_path.exists():
            parser.error(f"local media does not exist: {audio_path}")
        video_id = safe_id(args.video_id or audio_path.stem)
        source = {
            "input": args.source,
            "url": args.source_url,
            "video_id": video_id,
            "title": args.title or audio_path.stem,
            "duration_seconds": args.duration,
            "duration_string": None,
            "channel": args.channel,
            "upload_date": None,
            "manual_subtitle_languages": [],
            "automatic_caption_languages": [],
        }

    if args.duration is not None:
        source["duration_seconds"] = args.duration
    if args.clip and source.get("duration_seconds") and args.clip[1] > source["duration_seconds"]:
        parser.error("clip ends after the known media duration")

    glossary = read_glossary(args.glossary)
    prompt_parts = [args.prompt.strip()] if args.prompt.strip() else []
    if glossary:
        prompt_parts.append(", ".join(glossary))
    prompt = ". ".join(prompt_parts) or None

    device = choose_device(args.device)
    compute_type = args.compute_type
    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"

    from faster_whisper import WhisperModel

    print(f"Loading {args.model} on {device}/{compute_type}")
    model = WhisperModel(args.model, device=device, compute_type=compute_type)
    clip_timestamps: str | list[float] = "0"
    if args.clip:
        clip_timestamps = [args.clip[0], args.clip[1]]
    segments, info = model.transcribe(
        str(audio_path),
        language=args.language,
        beam_size=args.beam_size,
        vad_filter=True,
        condition_on_previous_text=args.condition_on_previous_text,
        initial_prompt=prompt,
        hotwords=", ".join(glossary) if glossary else None,
        clip_timestamps=clip_timestamps,
    )

    rows: list[dict[str, Any]] = []
    for index, segment in enumerate(segments, 1):
        row = {
            "number": index,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
            "avg_logprob": segment.avg_logprob,
            "no_speech_prob": segment.no_speech_prob,
        }
        rows.append(row)
        if index % 100 == 0:
            print(f"Processed {index} cues through {segment.end:.1f}s", flush=True)
    if not rows:
        raise RuntimeError("no speech segments were produced")

    stem = args.output / video_id
    srt_path = stem.with_suffix(".raw.srt")
    txt_path = stem.with_suffix(".raw.txt")
    segments_path = stem.with_suffix(".segments.json")
    manifest_path = stem.with_suffix(".manifest.json")

    srt_lines: list[str] = []
    for row in rows:
        srt_lines.extend(
            [
                str(row["number"]),
                f"{format_srt_timestamp(row['start'])} --> {format_srt_timestamp(row['end'])}",
                row["text"],
                "",
            ]
        )
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    txt_path.write_text(" ".join(row["text"] for row in rows) + "\n", encoding="utf-8")
    segments_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "transcription": {
            "model": args.model,
            "device": device,
            "compute_type": compute_type,
            "language_requested": args.language,
            "language_detected": info.language,
            "language_probability": info.language_probability,
            "beam_size": args.beam_size,
            "condition_on_previous_text": args.condition_on_previous_text,
            "glossary": glossary,
            "prompt": args.prompt,
            "clip_seconds": list(args.clip) if args.clip else None,
        },
        "audio_path": str(audio_path.resolve()),
        "outputs": {
            "srt": str(srt_path.resolve()),
            "txt": str(txt_path.resolve()),
            "segments": str(segments_path.resolve()),
        },
        "cue_count": len(rows),
        "coverage_seconds": [rows[0]["start"], rows[-1]["end"]],
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} cues")
    print(srt_path)
    print(txt_path)
    print(segments_path)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
