#!/usr/bin/env python3
"""Check GitHub Actions push CI runs for a fork branch."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from typing import Any


DEFAULT_REPO = "ranxi2001/karmada"
TERMINAL_OK = {"success", "skipped", "neutral"}
TERMINAL_BAD = {"failure", "timed_out", "cancelled", "startup_failure", "action_required"}
PENDING_STATUSES = {"queued", "requested", "waiting", "pending", "in_progress"}


@dataclass(frozen=True)
class CheckResult:
    code: int
    pending: bool
    failing: bool
    empty: bool


def git_output(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = result.stdout.strip()
    return value or None


def request_json(url: str, token: str | None) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "karmada-push-ci-check",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API returned HTTP {exc.code} for {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API request failed for {url}: {exc}") from exc

    return json.loads(data)


def runs_url(repo: str, branch: str, per_page: int) -> str:
    query = urllib.parse.urlencode({"branch": branch, "per_page": per_page})
    return f"https://api.github.com/repos/{repo}/actions/runs?{query}"


def normalize_sha(sha: str | None) -> str | None:
    if not sha:
        return None
    return sha.strip().lower()


def short_sha(sha: str | None) -> str:
    if not sha:
        return "-"
    return sha[:12]


def conclusion_for(run: dict[str, Any]) -> str:
    status = run.get("status") or "-"
    conclusion = run.get("conclusion")
    if status == "completed":
        return conclusion or "-"
    return status


def is_pending(run: dict[str, Any]) -> bool:
    status = run.get("status")
    return status in PENDING_STATUSES


def is_failing(run: dict[str, Any]) -> bool:
    return run.get("status") == "completed" and run.get("conclusion") in TERMINAL_BAD


def is_ok(run: dict[str, Any]) -> bool:
    return run.get("status") == "completed" and run.get("conclusion") in TERMINAL_OK


def filter_runs(runs: list[dict[str, Any]], sha: str | None) -> list[dict[str, Any]]:
    if not sha:
        return runs
    sha = sha.lower()
    return [run for run in runs if str(run.get("head_sha", "")).lower().startswith(sha)]


def load_runs(repo: str, branch: str, limit: int, token: str | None, sha: str | None) -> list[dict[str, Any]]:
    payload = request_json(runs_url(repo, branch, limit), token)
    runs = payload.get("workflow_runs", [])
    if not isinstance(runs, list):
        raise RuntimeError("GitHub API response did not include workflow_runs as a list")
    return filter_runs(runs, sha)


def load_jobs(jobs_url: str, token: str | None) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    page = 1
    while True:
        separator = "&" if "?" in jobs_url else "?"
        url = f"{jobs_url}{separator}{urllib.parse.urlencode({'per_page': 100, 'page': page})}"
        payload = request_json(url, token)
        chunk = payload.get("jobs", [])
        if not isinstance(chunk, list):
            raise RuntimeError("GitHub API response did not include jobs as a list")
        jobs.extend(chunk)
        if len(chunk) < 100:
            return jobs
        page += 1


def print_failed_jobs(runs: list[dict[str, Any]], token: str | None, mode: str) -> None:
    if mode == "none":
        return

    for run in runs:
        jobs_url = run.get("jobs_url")
        if not jobs_url:
            continue
        jobs = load_jobs(str(jobs_url), token)
        selected: list[dict[str, Any]]
        if mode == "all":
            selected = jobs
        else:
            selected = [
                job
                for job in jobs
                if job.get("status") == "completed" and job.get("conclusion") in TERMINAL_BAD
            ]
        if not selected:
            continue
        print(f"\nJobs for {run.get('name', '-')}:")
        for job in selected:
            job_line = f"  - {job.get('name', '-')}: {job.get('status', '-')}/{job.get('conclusion') or '-'}"
            if job.get("html_url"):
                job_line += f" {job.get('html_url')}"
            print(job_line)
            for step in job.get("steps") or []:
                if mode != "all" and step.get("conclusion") not in TERMINAL_BAD:
                    continue
                print(
                    "      step: "
                    f"{step.get('name', '-')} "
                    f"{step.get('status', '-')}/{step.get('conclusion') or '-'}"
                )


def summarize_runs(
    repo: str,
    branch: str,
    sha: str | None,
    runs: list[dict[str, Any]],
    token: str | None,
    show_jobs: str,
) -> CheckResult:
    print(f"repo: {repo}")
    print(f"branch: {branch}")
    print(f"sha: {sha or '-'}")

    if not runs:
        print("summary: no matching workflow runs found")
        return CheckResult(code=3, pending=False, failing=False, empty=True)

    counts = Counter(conclusion_for(run) for run in runs)
    summary = ", ".join(f"{value} {key}" for key, value in sorted(counts.items()))
    print(f"summary: {summary}")

    for run in sorted(runs, key=lambda item: item.get("created_at", ""), reverse=True):
        name = run.get("name") or run.get("display_title") or "-"
        status = run.get("status") or "-"
        conclusion = run.get("conclusion") or "-"
        event = run.get("event") or "-"
        run_sha = short_sha(run.get("head_sha"))
        url = run.get("html_url") or "-"
        print(f"- {name}: {status}/{conclusion} event={event} sha={run_sha} {url}")

    print_failed_jobs(runs, token, show_jobs)

    pending = any(is_pending(run) for run in runs)
    failing = any(is_failing(run) for run in runs)
    failed_job_seen = False
    if not failing and show_jobs != "none":
        for run in runs:
            jobs_url = run.get("jobs_url")
            if not jobs_url:
                continue
            jobs = load_jobs(str(jobs_url), token)
            if any(job.get("status") == "completed" and job.get("conclusion") in TERMINAL_BAD for job in jobs):
                failed_job_seen = True
                break
    unknown_completed = any(
        run.get("status") == "completed"
        and not is_ok(run)
        and not is_failing(run)
        for run in runs
    )

    if failing or failed_job_seen or unknown_completed:
        return CheckResult(code=1, pending=pending, failing=True, empty=False)
    if pending:
        return CheckResult(code=2, pending=True, failing=False, empty=False)
    return CheckResult(code=0, pending=False, failing=False, empty=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO))
    parser.add_argument("--branch", default=None, help="Branch name. Defaults to current git branch.")
    parser.add_argument("--sha", default=None, help="Head SHA or prefix. Defaults to current git HEAD.")
    parser.add_argument("--limit", type=int, default=30, help="Number of branch workflow runs to fetch.")
    parser.add_argument("--watch", action="store_true", help="Poll until matching runs are terminal.")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between --watch polls.")
    parser.add_argument(
        "--show-jobs",
        choices=("none", "failed", "all"),
        default="failed",
        help="Show job details for failed or all runs.",
    )
    parser.add_argument(
        "--no-git-defaults",
        action="store_true",
        help="Do not infer branch or SHA from the current git worktree.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    branch = args.branch
    sha = normalize_sha(args.sha)
    if not args.no_git_defaults:
        branch = branch or git_output(["rev-parse", "--abbrev-ref", "HEAD"])
        sha = sha or normalize_sha(git_output(["rev-parse", "HEAD"]))

    if not branch:
        print("error: --branch is required outside a git worktree", file=sys.stderr)
        return 64

    while True:
        stamp = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
        if args.watch:
            print(f"\n[{stamp}] checking GitHub Actions")
        try:
            runs = load_runs(args.repo, branch, args.limit, token, sha)
            result = summarize_runs(args.repo, branch, sha, runs, token, args.show_jobs)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 70

        if not args.watch or result.code in (0, 1, 3):
            return result.code

        time.sleep(max(args.interval, 5))


if __name__ == "__main__":
    raise SystemExit(main())
