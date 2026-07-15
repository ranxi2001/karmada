#!/usr/bin/env python3
"""Render a Mermaid source with the official mermaid-cli."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile


PINNED_CLI_VERSION = "11.16.0"
SUPPORTED_OUTPUTS = {".png", ".svg", ".pdf"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render .mmd to PNG, SVG, or PDF with official mermaid-cli."
    )
    parser.add_argument("input", type=Path, help="Mermaid source file")
    parser.add_argument("-o", "--output", type=Path, help="Output path (default: <input>.png)")
    parser.add_argument(
        "--backend",
        choices=("auto", "mmdc", "npx"),
        default="auto",
        help="Renderer backend; npx is explicit because it downloads a package",
    )
    parser.add_argument("--cli-version", default=PINNED_CLI_VERSION)
    parser.add_argument(
        "--theme",
        choices=("default", "forest", "dark", "neutral"),
        default="default",
    )
    parser.add_argument("--background", default="white")
    parser.add_argument("--width", type=int, default=2000)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--config", type=Path, help="Mermaid JSON config file")
    parser.add_argument("--puppeteer-config", type=Path, help="Existing Puppeteer JSON config")
    parser.add_argument("--no-sandbox", action="store_true", help="Pass Chromium no-sandbox flags")
    parser.add_argument("--dry-run", action="store_true", help="Print the command without running it")
    return parser.parse_args()


def resolve_command(backend: str, version: str) -> list[str]:
    path_mmdc = shutil.which("mmdc")
    local_mmdc = Path.cwd() / "node_modules" / ".bin" / "mmdc"

    if backend in {"auto", "mmdc"}:
        if path_mmdc:
            return [path_mmdc]
        if local_mmdc.is_file():
            return [str(local_mmdc)]
        if backend == "mmdc":
            raise RuntimeError("mmdc not found on PATH or in ./node_modules/.bin")

    if backend == "npx":
        npx = shutil.which("npx")
        if not npx:
            raise RuntimeError("npx not found")
        return [
            npx,
            "--yes",
            "--package",
            f"@mermaid-js/mermaid-cli@{version}",
            "--",
            "mmdc",
        ]

    raise RuntimeError(
        "mmdc not found. Install @mermaid-js/mermaid-cli or rerun with "
        "--backend npx after approving the package download."
    )


def find_browser() -> Path | None:
    configured = os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    if configured and Path(configured).is_file():
        return Path(configured).resolve()

    for executable in (
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "chrome",
    ):
        path = shutil.which(executable)
        if path:
            return Path(path).resolve()

    playwright_cache = Path.home() / ".cache" / "ms-playwright"
    patterns = (
        "chromium-*/chrome-linux*/chrome",
        "chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell",
    )
    for pattern in patterns:
        candidates = sorted(playwright_cache.glob(pattern), reverse=True)
        if candidates:
            return candidates[0].resolve()
    return None


def validate_paths(source: Path, output: Path, args: argparse.Namespace) -> None:
    if not source.is_file():
        raise RuntimeError(f"input does not exist: {source}")
    if output.suffix.lower() not in SUPPORTED_OUTPUTS:
        raise RuntimeError("output extension must be .png, .svg, or .pdf")
    if args.width <= 0:
        raise RuntimeError("--width must be positive")
    if args.scale <= 0:
        raise RuntimeError("--scale must be positive")
    if args.config and not args.config.is_file():
        raise RuntimeError(f"config does not exist: {args.config}")
    if args.puppeteer_config and not args.puppeteer_config.is_file():
        raise RuntimeError(f"Puppeteer config does not exist: {args.puppeteer_config}")


def render(args: argparse.Namespace) -> int:
    source = args.input.resolve()
    output = (args.output or args.input.with_suffix(".png")).resolve()
    validate_paths(source, output, args)
    command = resolve_command(args.backend, args.cli_version)
    output.parent.mkdir(parents=True, exist_ok=True)

    command.extend(
        [
            "-i",
            str(source),
            "-o",
            str(output),
            "-t",
            args.theme,
            "-b",
            args.background,
            "-w",
            str(args.width),
            "-s",
            str(args.scale),
        ]
    )
    if args.config:
        command.extend(["-c", str(args.config.resolve())])

    browser = find_browser()
    temporary_config: tempfile.TemporaryDirectory[str] | None = None
    puppeteer_config = args.puppeteer_config
    needs_no_sandbox = args.no_sandbox or (hasattr(os, "geteuid") and os.geteuid() == 0)
    if not puppeteer_config and (needs_no_sandbox or browser):
        temporary_config = tempfile.TemporaryDirectory(prefix="project-mermaid-")
        config_path = Path(temporary_config.name) / "puppeteer.json"
        config: dict[str, object] = {}
        if needs_no_sandbox:
            config["args"] = ["--no-sandbox", "--disable-setuid-sandbox"]
        if browser:
            config["executablePath"] = str(browser)
        config_path.write_text(json.dumps(config), encoding="utf-8")
        puppeteer_config = config_path
    if puppeteer_config:
        command.extend(["-p", str(puppeteer_config.resolve())])

    print(shlex.join(command))
    if args.dry_run:
        if temporary_config:
            temporary_config.cleanup()
        return 0

    environment = os.environ.copy()
    if Path(command[0]).name in {"npx", "npx.cmd"} and browser:
        environment["PUPPETEER_SKIP_DOWNLOAD"] = "true"

    try:
        result = subprocess.run(command, check=False, env=environment)
    finally:
        if temporary_config:
            temporary_config.cleanup()

    if result.returncode != 0:
        if output.exists():
            output.unlink()
        return result.returncode
    if not output.is_file() or output.stat().st_size == 0:
        print(f"render completed without a usable output: {output}", file=sys.stderr)
        return 1

    print(f"rendered: {output}")
    return 0


def main() -> int:
    args = parse_args()
    try:
        return render(args)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
