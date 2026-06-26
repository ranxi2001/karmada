#!/usr/bin/env python3
"""Fetch Karmada issue/PR discussion context as JSON."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def request_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "karmada-issue-discussion-skill",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"error": "not_found", "url": url}
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("number", type=int, help="GitHub issue or PR number")
    parser.add_argument("--repo", default="karmada-io/karmada", help="owner/repo")
    args = parser.parse_args()

    base = f"https://api.github.com/repos/{args.repo}"
    number = args.number

    issue = request_json(f"{base}/issues/{number}")
    comments = request_json(f"{base}/issues/{number}/comments?per_page=100")

    result = {
        "repo": args.repo,
        "number": number,
        "issue": issue,
        "comments": comments,
    }

    if isinstance(issue, dict) and issue.get("pull_request"):
        result["pull_request"] = request_json(f"{base}/pulls/{number}")
        result["pull_files"] = request_json(f"{base}/pulls/{number}/files?per_page=100")
        result["pull_commits"] = request_json(f"{base}/pulls/{number}/commits?per_page=100")
        result["review_comments"] = request_json(f"{base}/pulls/{number}/comments?per_page=100")

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
