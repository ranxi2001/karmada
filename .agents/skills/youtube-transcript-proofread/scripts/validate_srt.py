#!/usr/bin/env python3
"""Validate SRT structure, timing, duration bounds, and common ASR anomalies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


TIMESTAMP_RE = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2})[,.](\d{3}) --> "
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})$"
)


@dataclass(frozen=True)
class Cue:
    number: int
    start: float
    end: float
    text: str


def parse_timestamp(parts: tuple[str, ...]) -> float:
    hours, minutes, seconds, millis = (int(value) for value in parts)
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def format_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def parse_srt(path: Path) -> list[Cue]:
    raw = path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        raise ValueError("SRT is empty")

    cues: list[Cue] = []
    blocks = re.split(r"(?:\r?\n){2,}", raw)
    for block_index, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if len(lines) < 3:
            raise ValueError(f"block {block_index} has fewer than 3 lines")
        try:
            number = int(lines[0].strip())
        except ValueError as exc:
            raise ValueError(f"block {block_index} has invalid cue number") from exc
        match = TIMESTAMP_RE.match(lines[1].strip())
        if not match:
            raise ValueError(f"cue {number} has invalid timestamp line: {lines[1]!r}")
        values = match.groups()
        start = parse_timestamp(values[:4])
        end = parse_timestamp(values[4:])
        text = " ".join(line.strip() for line in lines[2:] if line.strip())
        cues.append(Cue(number=number, start=start, end=end, text=text))
    return cues


def duration_from_manifest(path: Path) -> float | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data.get("source", {}).get("duration_seconds")
    return float(value) if value is not None else None


def normalized_text(value: str) -> str:
    return re.sub(r"\W+", "", value.casefold(), flags=re.UNICODE)


def validate(
    cues: list[Cue],
    duration: float | None,
    overrun_tolerance: float,
    long_segment: float,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    previous_start = -1.0
    previous_number = 0
    repeated: list[Cue] = []
    previous_normalized = ""

    for cue in cues:
        if cue.number != previous_number + 1:
            errors.append(f"cue numbering jumps from {previous_number} to {cue.number}")
        if cue.start < previous_start:
            errors.append(f"cue {cue.number} starts before the previous cue")
        if cue.end < cue.start:
            errors.append(f"cue {cue.number} ends before it starts")
        if not cue.text:
            warnings.append(f"cue {cue.number} has empty text")
        if cue.end - cue.start > long_segment:
            warnings.append(
                f"cue {cue.number} lasts {cue.end - cue.start:.1f}s "
                f"({format_timestamp(cue.start)}-{format_timestamp(cue.end)})"
            )
        if duration is not None and cue.end > duration + overrun_tolerance:
            errors.append(
                f"cue {cue.number} ends at {cue.end:.3f}s, beyond media duration "
                f"{duration:.3f}s"
            )

        current_normalized = normalized_text(cue.text)
        if current_normalized and current_normalized == previous_normalized:
            repeated.append(cue)
        else:
            if len(repeated) >= 2:
                first = repeated[0].number - 1
                last = repeated[-1].number
                warnings.append(f"same text repeats in cues {first}-{last}")
            repeated = []
        previous_normalized = current_normalized
        previous_start = cue.start
        previous_number = cue.number

    if len(repeated) >= 2:
        first = repeated[0].number - 1
        last = repeated[-1].number
        warnings.append(f"same text repeats in cues {first}-{last}")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("srt", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--duration", type=float, help="Media duration in seconds")
    parser.add_argument("--overrun-tolerance", type=float, default=1.0)
    parser.add_argument("--long-segment", type=float, default=30.0)
    parser.add_argument("--fail-on-warning", action="store_true")
    args = parser.parse_args()

    duration = args.duration
    if duration is None and args.manifest:
        duration = duration_from_manifest(args.manifest)

    try:
        cues = parse_srt(args.srt)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors, warnings = validate(
        cues,
        duration=duration,
        overrun_tolerance=args.overrun_tolerance,
        long_segment=args.long_segment,
    )
    for message in warnings:
        print(f"WARNING: {message}")
    for message in errors:
        print(f"ERROR: {message}", file=sys.stderr)

    print(
        f"Checked {len(cues)} cues; coverage "
        f"{format_timestamp(cues[0].start)}-{format_timestamp(cues[-1].end)}; "
        f"errors={len(errors)} warnings={len(warnings)}"
    )
    if errors or (warnings and args.fail_on_warning):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
