#!/usr/bin/env python3
"""Audit whether run-scoped artifacts can support a selected Actions job attempt."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


JOB_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/actions/runs/"
    r"(?P<run_id>\d+)/job/(?P<job_id>\d+)(?:[/?#].*)?$"
)


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_job_url(value: str) -> dict[str, str]:
    match = JOB_URL_RE.match(value)
    if not match:
        raise ValueError(
            "expected https://github.com/<owner>/<repo>/actions/runs/<run_id>/job/<job_id>"
        )
    return match.groupdict()


def api_get(url: str, token: str | None) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "codex-e2e-run-attempt-audit",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def fetch_artifacts(owner: str, repo: str, run_id: str, token: str | None) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({"per_page": 100, "page": page})
        payload = api_get(
            f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts?{query}",
            token,
        )
        batch = payload.get("artifacts", [])
        artifacts.extend(batch)
        if len(batch) < 100:
            return artifacts
        page += 1


def classify_artifact(
    artifact: dict[str, Any], job: dict[str, Any], run: dict[str, Any]
) -> tuple[str, str]:
    job_attempt = job.get("run_attempt")
    run_attempt = run.get("run_attempt")
    if not isinstance(job_attempt, int) or not isinstance(run_attempt, int):
        return "ambiguous", "job or run is missing run_attempt"
    if job_attempt != run_attempt:
        return (
            "not_attributable",
            f"job attempt {job_attempt} differs from currently exposed run attempt {run_attempt}",
        )

    created = parse_time(artifact.get("created_at"))
    attempt_start = parse_time(run.get("run_started_at")) or parse_time(run.get("created_at"))
    if created is None or attempt_start is None:
        return "ambiguous", "artifact creation or attempt start timestamp is missing"
    if created < attempt_start:
        return "not_attributable", "artifact predates the selected attempt start"
    return "attempt_compatible", "artifact was created after the selected current attempt started"


def build_report(
    target: dict[str, str],
    job: dict[str, Any],
    run: dict[str, Any],
    artifacts: list[dict[str, Any]],
    artifact_name: str | None = None,
) -> dict[str, Any]:
    if artifact_name:
        artifacts = [item for item in artifacts if item.get("name") == artifact_name]

    audited = []
    counts = {"attempt_compatible": 0, "not_attributable": 0, "ambiguous": 0}
    expired_count = 0
    for artifact in artifacts:
        classification, reason = classify_artifact(artifact, job, run)
        counts[classification] += 1
        expired = bool(artifact.get("expired"))
        expired_count += int(expired)
        audited.append(
            {
                "id": artifact.get("id"),
                "name": artifact.get("name"),
                "created_at": artifact.get("created_at"),
                "expired": expired,
                "availability": "expired" if expired else "available",
                "classification": classification,
                "reason": reason,
            }
        )

    job_attempt = job.get("run_attempt")
    run_attempt = run.get("run_attempt")
    if job_attempt != run_attempt:
        conclusion = "selected job is from an older attempt; current run artifacts cannot prove it"
    elif not audited:
        conclusion = "no matching artifacts were returned"
    elif counts["ambiguous"]:
        conclusion = "artifact ownership is ambiguous; disclose the gap"
    elif counts["attempt_compatible"] and expired_count == counts["attempt_compatible"]:
        conclusion = "listed artifacts match the selected attempt but are expired and unavailable"
    elif counts["attempt_compatible"]:
        conclusion = "listed artifacts are compatible with the selected current attempt"
    else:
        conclusion = "no listed artifact is attributable to the selected attempt"

    return {
        "target": target,
        "job": {
            "id": job.get("id"),
            "name": job.get("name"),
            "run_id": job.get("run_id"),
            "run_attempt": job_attempt,
            "started_at": job.get("started_at"),
            "completed_at": job.get("completed_at"),
            "conclusion": job.get("conclusion"),
        },
        "run": {
            "id": run.get("id"),
            "run_attempt": run_attempt,
            "created_at": run.get("created_at"),
            "run_started_at": run.get("run_started_at"),
            "updated_at": run.get("updated_at"),
            "conclusion": run.get("conclusion"),
        },
        "artifacts": audited,
        "summary": {**counts, "expired": expired_count, "conclusion": conclusion},
    }


def validate_target(target: dict[str, str], job: dict[str, Any], run: dict[str, Any]) -> None:
    expected = {
        "job id": (target["job_id"], job.get("id")),
        "job run id": (target["run_id"], job.get("run_id")),
        "run id": (target["run_id"], run.get("id")),
    }
    for label, (url_value, api_value) in expected.items():
        if str(api_value) != url_value:
            raise ValueError(f"{label} mismatch: URL has {url_value}, API has {api_value}")


def load_fixture(fixture_dir: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    job = json.loads((fixture_dir / "job.json").read_text(encoding="utf-8"))
    run = json.loads((fixture_dir / "run.json").read_text(encoding="utf-8"))
    payload = json.loads((fixture_dir / "artifacts.json").read_text(encoding="utf-8"))
    artifacts = payload.get("artifacts", payload) if isinstance(payload, dict) else payload
    return job, run, artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_url")
    parser.add_argument("--artifact-name", help="only audit an exact artifact name")
    parser.add_argument("--fixture-dir", type=Path, help="read job.json, run.json, artifacts.json")
    args = parser.parse_args()

    try:
        target = parse_job_url(args.job_url)
        if args.fixture_dir:
            job, run, artifacts = load_fixture(args.fixture_dir)
        else:
            token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
            owner, repo = target["owner"], target["repo"]
            job = api_get(
                f"https://api.github.com/repos/{owner}/{repo}/actions/jobs/{target['job_id']}",
                token,
            )
            run = api_get(
                f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{target['run_id']}",
                token,
            )
            artifacts = fetch_artifacts(owner, repo, target["run_id"], token)
        validate_target(target, job, run)
        report = build_report(target, job, run, artifacts, args.artifact_name)
    except (ValueError, OSError, KeyError, json.JSONDecodeError, urllib.error.URLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
