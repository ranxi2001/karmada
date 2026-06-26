#!/usr/bin/env python3
"""Fetch Karmada PR status and review surface."""

import argparse
import json
import os
import sys
import urllib.request


def request_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "karmada-pr-management-skill",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("number", type=int, help="GitHub PR number")
    parser.add_argument("--repo", default="karmada-io/karmada", help="owner/repo")
    args = parser.parse_args()

    base = f"https://api.github.com/repos/{args.repo}"
    pr = request_json(f"{base}/pulls/{args.number}")
    files = request_json(f"{base}/pulls/{args.number}/files?per_page=100")
    commits = request_json(f"{base}/pulls/{args.number}/commits?per_page=100")
    issue_comments = request_json(f"{base}/issues/{args.number}/comments?per_page=100")
    review_comments = request_json(f"{base}/pulls/{args.number}/comments?per_page=100")

    result = {
        "number": args.number,
        "title": pr.get("title") if isinstance(pr, dict) else None,
        "state": pr.get("state") if isinstance(pr, dict) else None,
        "merged": pr.get("merged") if isinstance(pr, dict) else None,
        "labels": [label["name"] for label in pr.get("labels", [])] if isinstance(pr, dict) else [],
        "draft": pr.get("draft") if isinstance(pr, dict) else None,
        "changed_files": pr.get("changed_files") if isinstance(pr, dict) else None,
        "additions": pr.get("additions") if isinstance(pr, dict) else None,
        "deletions": pr.get("deletions") if isinstance(pr, dict) else None,
        "files": [
            {
                "filename": f.get("filename"),
                "status": f.get("status"),
                "additions": f.get("additions"),
                "deletions": f.get("deletions"),
            }
            for f in files
            if isinstance(f, dict)
        ]
        if isinstance(files, list)
        else files,
        "commits": [
            {
                "sha": c.get("sha", "")[:7],
                "message": c.get("commit", {}).get("message", "").split("\n")[0],
            }
            for c in commits
            if isinstance(c, dict)
        ]
        if isinstance(commits, list)
        else commits,
        "issue_comments_count": len(issue_comments) if isinstance(issue_comments, list) else None,
        "review_comments_count": len(review_comments) if isinstance(review_comments, list) else None,
        "review_comments": [
            {
                "user": c.get("user", {}).get("login"),
                "path": c.get("path"),
                "line": c.get("line") or c.get("original_line"),
                "body": c.get("body", "")[:500],
            }
            for c in review_comments[:20]
            if isinstance(c, dict)
        ]
        if isinstance(review_comments, list)
        else review_comments,
    }

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
