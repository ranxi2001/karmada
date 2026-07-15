#!/usr/bin/env python3
"""Convert an SRT transcript into deterministic Markdown review chunks."""

from __future__ import annotations

import argparse
from pathlib import Path

from validate_srt import Cue, format_timestamp, parse_srt


def display_timestamp(seconds: float) -> str:
    return format_timestamp(seconds).replace(",", ".")


def write_chunk(
    output_dir: Path,
    index: int,
    cues: list[Cue],
    title: str,
    source_url: str,
) -> Path:
    start = cues[0].start
    end = cues[-1].end
    lines = [
        f"# Transcript Review Chunk {index:03d}",
        "",
        f"Title: {title or 'Unknown'}",
        f"Source: {source_url or 'Not provided'}",
        f"Coverage: `{display_timestamp(start)}-{display_timestamp(end)}`",
        "",
        "Correct terminology and punctuation without paraphrasing. Preserve qualifiers, "
        "mark uncertain audio, and do not infer named speakers.",
        "",
        "## Raw ASR",
        "",
    ]
    for cue in cues:
        lines.append(
            f"- [`{display_timestamp(cue.start)}-{display_timestamp(cue.end)}`] "
            f"{cue.text}"
        )
    path = output_dir / f"chunk-{index:03d}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("srt", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--minutes", type=float, default=15.0)
    parser.add_argument("--title", default="")
    parser.add_argument("--source-url", default="")
    args = parser.parse_args()

    if args.minutes <= 0:
        parser.error("--minutes must be positive")
    cues = parse_srt(args.srt)
    args.output.mkdir(parents=True, exist_ok=True)
    chunk_seconds = args.minutes * 60
    groups: list[list[Cue]] = []
    current: list[Cue] = []
    boundary = (int(cues[0].start // chunk_seconds) + 1) * chunk_seconds

    for cue in cues:
        if current and cue.start >= boundary:
            groups.append(current)
            current = []
            while cue.start >= boundary:
                boundary += chunk_seconds
        current.append(cue)
    if current:
        groups.append(current)

    for index, group in enumerate(groups, 1):
        path = write_chunk(
            args.output,
            index=index,
            cues=group,
            title=args.title,
            source_url=args.source_url,
        )
        print(path)
    print(f"Created {len(groups)} review chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
