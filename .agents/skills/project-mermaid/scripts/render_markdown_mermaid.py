#!/usr/bin/env python3
"""Extract and render every Mermaid fence from a Markdown file."""

from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


OPEN_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})[ \t]*mermaid[ \t]*$", re.IGNORECASE)


@dataclass(frozen=True)
class MermaidFence:
    index: int
    start_line: int
    end_line: int
    source: str


def extract_mermaid_fences(markdown: str) -> list[MermaidFence]:
    lines = markdown.splitlines()
    fences: list[MermaidFence] = []
    opening: tuple[str, int, int] | None = None
    body: list[str] = []

    for line_number, line in enumerate(lines, start=1):
        if opening is None:
            match = OPEN_RE.match(line)
            if match:
                marker = match.group("fence")
                opening = (marker[0], len(marker), line_number)
                body = []
            continue

        marker_char, marker_length, start_line = opening
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        close_match = re.match(rf"^{re.escape(marker_char)}{{{marker_length},}}[ \t]*$", stripped)
        if indent <= 3 and close_match:
            fences.append(
                MermaidFence(
                    index=len(fences) + 1,
                    start_line=start_line,
                    end_line=line_number,
                    source="\n".join(body).rstrip() + "\n",
                )
            )
            opening = None
            body = []
        else:
            body.append(line)

    if opening is not None:
        raise ValueError(f"unclosed Mermaid fence starting at line {opening[2]}")
    return fences


def output_dimensions(path: Path) -> tuple[float | None, float | None]:
    if path.suffix.lower() == ".png":
        with path.open("rb") as stream:
            header = stream.read(24)
        if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n":
            width, height = struct.unpack(">II", header[16:24])
            return float(width), float(height)
    if path.suffix.lower() == ".svg":
        root = ET.parse(path).getroot()

        def number(value: str | None) -> float | None:
            if not value:
                return None
            match = re.match(r"^[ \t]*([0-9]+(?:\.[0-9]+)?)", value)
            return float(match.group(1)) if match else None

        width, height = number(root.get("width")), number(root.get("height"))
        if (width is None or height is None) and root.get("viewBox"):
            parts = root.get("viewBox", "").replace(",", " ").split()
            if len(parts) == 4:
                width, height = float(parts[2]), float(parts[3])
        return width, height
    return None, None


def render_fences(args: argparse.Namespace, fences: list[MermaidFence]) -> list[dict[str, object]]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    renderer = Path(__file__).with_name("render_mermaid.py")
    manifest: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="markdown-mermaid-") as temporary:
        temporary_dir = Path(temporary)
        for fence in fences:
            stem = f"mermaid-{fence.index:02d}-line-{fence.start_line}"
            source = temporary_dir / f"{stem}.mmd"
            source.write_text(fence.source, encoding="utf-8")
            output = output_dir / f"{stem}.{args.format}"
            command = [
                sys.executable,
                str(renderer),
                str(source),
                "-o",
                str(output),
                "--backend",
                args.backend,
                "--width",
                str(args.width),
                "--scale",
                str(args.scale),
            ]
            if args.cli_version:
                command.extend(["--cli-version", args.cli_version])
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode:
                detail = result.stderr.strip() or result.stdout.strip()
                raise RuntimeError(
                    f"fence {fence.index} (lines {fence.start_line}-{fence.end_line}) failed: {detail}"
                )
            width, height = output_dimensions(output)
            if args.keep_sources:
                (output_dir / f"{stem}.mmd").write_text(fence.source, encoding="utf-8")
            manifest.append(
                {
                    "index": fence.index,
                    "start_line": fence.start_line,
                    "end_line": fence.end_line,
                    "output": str(output),
                    "bytes": output.stat().st_size,
                    "width": width,
                    "height": height,
                }
            )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--format", choices=("png", "svg", "pdf"), default="png")
    parser.add_argument("--backend", choices=("auto", "mmdc", "npx"), default="auto")
    parser.add_argument("--cli-version")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--keep-sources", action="store_true")
    args = parser.parse_args()

    try:
        fences = extract_mermaid_fences(args.markdown.read_text(encoding="utf-8"))
        if not fences:
            raise ValueError("no fenced Mermaid blocks found")
        manifest = render_fences(args, fences)
    except (OSError, ValueError, RuntimeError, ET.ParseError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    json.dump({"markdown": str(args.markdown.resolve()), "diagrams": manifest}, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
