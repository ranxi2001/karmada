#!/usr/bin/env python3
"""Measure the reviewer-visible size of an upstream Markdown draft."""

import argparse
import json
import re
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count visible words and nonblank lines after removing HTML comments."
    )
    parser.add_argument("path", nargs="?", default="-", help="Markdown file, or - for stdin")
    parser.add_argument("--limit", type=int, help="Optional soft word limit")
    parser.add_argument(
        "--fail-over-limit",
        action="store_true",
        help="Exit with status 1 when the visible word count exceeds --limit",
    )
    return parser.parse_args()


def read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.fail_over_limit and args.limit is None:
        raise SystemExit("--fail-over-limit requires --limit")

    raw = read_text(args.path).replace("\r\n", "\n").replace("\r", "\n")
    visible = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL).strip()
    words = re.findall(r"\S+", visible)
    nonblank_lines = [line for line in visible.splitlines() if line.strip()]
    over_limit = args.limit is not None and len(words) > args.limit

    result = {
        "visible_chars": len(visible),
        "visible_words": len(words),
        "nonblank_lines": len(nonblank_lines),
        "html_comment_chars_removed": len(raw) - len(re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)),
        "soft_limit": args.limit,
        "over_limit": over_limit,
    }
    print(json.dumps(result, sort_keys=True))
    return 1 if args.fail_over_limit and over_limit else 0


if __name__ == "__main__":
    raise SystemExit(main())
