#!/usr/bin/env python3
"""Print a compact GitHub issue/PR briefing for Karmada discussion work."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request


def github_headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "karmada-thread-brief-skill",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request_json(url):
    req = urllib.request.Request(url, headers=github_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body), resp.headers
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed: {exc.code} {url}\n{detail}") from exc


def next_link(link_header):
    for part in link_header.split(","):
        if 'rel="next"' in part:
            match = re.search(r"<([^>]+)>", part)
            if match:
                return match.group(1)
    return None


def request_all_pages(url):
    items = []
    while url:
        data, headers = request_json(url)
        if not isinstance(data, list):
            return data
        items.extend(data)
        url = next_link(headers.get("Link", ""))
    return items


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def clip(text, limit):
    text = clean_text(text)
    if limit <= 0 or len(text) <= limit:
        return text
    return text[:limit].rstrip() + " ..."


def login(obj):
    user = obj.get("user") if isinstance(obj, dict) else None
    name = user.get("login") if isinstance(user, dict) else None
    return f"@{name}" if name else "-"


def names(items, key="name"):
    values = [item.get(key) for item in items or [] if isinstance(item, dict) and item.get(key)]
    return ", ".join(values) if values else "-"


def bool_text(value):
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "-"


def limited_items(items, limit):
    if limit <= 0 or len(items) <= limit:
        for item in items:
            yield item
        return

    head = min(5, max(1, limit // 4))
    tail = max(0, limit - head)
    for item in items[:head]:
        yield item
    yield {"_omitted": len(items) - head - tail}
    for item in items[-tail:]:
        yield item


def print_comment_list(title, comments, limit, chars):
    print(f"## {title}")
    if not comments:
        print("- none")
        print()
        return

    shown_index = 0
    for comment in limited_items(comments, limit):
        if "_omitted" in comment:
            print(f"- ... omitted {comment['_omitted']} middle comments ...")
            continue
        shown_index += 1
        created = comment.get("created_at") or comment.get("submitted_at") or "-"
        assoc = comment.get("author_association") or comment.get("state") or "-"
        path = comment.get("path")
        line = comment.get("line") or comment.get("original_line")
        location = f" `{path}:{line}`" if path and line else f" `{path}`" if path else ""
        url = comment.get("html_url") or comment.get("pull_request_url") or "-"
        body = clip(comment.get("body", ""), chars) or "-"
        print(f"{shown_index}. {login(comment)} ({assoc}, {created}){location}")
        print(f"   {url}")
        print(f"   {body}")
    print()


def print_assign_signals(comment_groups):
    assign_comments = []
    pattern = re.compile(r"(^|\s)/(unassign|assign)\b", re.IGNORECASE)
    for source, comments in comment_groups:
        for comment in comments:
            body = comment.get("body", "")
            if pattern.search(body):
                assign_comments.append((source, comment))

    print("## Assign Signals")
    if not assign_comments:
        print("- none")
    for source, comment in assign_comments:
        created = comment.get("created_at") or comment.get("submitted_at") or "-"
        print(f"- {source}: {login(comment)} at {created}: {clip(comment.get('body', ''), 160)}")
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int, help="GitHub issue or PR number")
    parser.add_argument("--repo", default="karmada-io/karmada", help="owner/repo")
    parser.add_argument("--body-chars", type=int, default=1200, help="issue/PR body snippet length")
    parser.add_argument("--comment-chars", type=int, default=500, help="comment snippet length")
    parser.add_argument("--comments-limit", type=int, default=60, help="issue comments to show; 0 means all")
    parser.add_argument("--review-comments-limit", type=int, default=60, help="PR review comments to show; 0 means all")
    args = parser.parse_args()

    base = f"https://api.github.com/repos/{args.repo}"
    issue, _ = request_json(f"{base}/issues/{args.number}")
    comments = request_all_pages(f"{base}/issues/{args.number}/comments?per_page=100")
    is_pr = bool(issue.get("pull_request"))
    pr = None
    files = []
    commits = []
    reviews = []
    review_comments = []

    if is_pr:
        pr, _ = request_json(f"{base}/pulls/{args.number}")
        files = request_all_pages(f"{base}/pulls/{args.number}/files?per_page=100")
        commits = request_all_pages(f"{base}/pulls/{args.number}/commits?per_page=100")
        reviews = request_all_pages(f"{base}/pulls/{args.number}/reviews?per_page=100")
        review_comments = request_all_pages(f"{base}/pulls/{args.number}/comments?per_page=100")

    print(f"# {args.repo}#{args.number}")
    print(f"- Type: {'PR' if is_pr else 'issue'}")
    print(f"- URL: {issue.get('html_url', '-')}")
    print(f"- Title: {issue.get('title', '-')}")
    print(f"- State: {issue.get('state', '-')}")
    print(f"- Author: {login(issue)} ({issue.get('author_association', '-')})")
    print(f"- Created: {issue.get('created_at', '-')}")
    print(f"- Updated: {issue.get('updated_at', '-')}")
    print(f"- Labels: {names(issue.get('labels', []))}")
    print(f"- Assignees: {names(issue.get('assignees', []), key='login')}")
    print(f"- Milestone: {(issue.get('milestone') or {}).get('title', '-') if isinstance(issue.get('milestone'), dict) else '-'}")
    print(f"- Issue comments: {len(comments) if isinstance(comments, list) else '-'}")
    print()

    print("## Body Snippet")
    print(clip(issue.get("body", ""), args.body_chars) or "-")
    print()

    if isinstance(comments, list):
        signal_groups = [("issue comments", comments)]
        if is_pr:
            if isinstance(reviews, list):
                signal_groups.append(("PR reviews", reviews))
            if isinstance(review_comments, list):
                signal_groups.append(("PR review comments", review_comments))
        print_assign_signals(signal_groups)
        print_comment_list("Issue Comments", comments, args.comments_limit, args.comment_chars)

    if not is_pr:
        return 0

    base_ref = pr.get("base", {}).get("ref") if isinstance(pr.get("base"), dict) else "-"
    head = pr.get("head", {}) if isinstance(pr.get("head"), dict) else {}
    head_ref = f"{head.get('label', '-')}"

    print("## PR Surface")
    print(f"- Base: {base_ref}")
    print(f"- Head: {head_ref}")
    print(f"- Draft: {bool_text(pr.get('draft'))}")
    print(f"- Mergeable state: {pr.get('mergeable_state', '-')}")
    print(f"- Changed files: {pr.get('changed_files', '-')}")
    print(f"- Additions/deletions: +{pr.get('additions', '-')} / -{pr.get('deletions', '-')}")
    print(f"- Commits: {len(commits) if isinstance(commits, list) else '-'}")
    print()

    print("## PR Files")
    if not files:
        print("- none")
    for item in files if isinstance(files, list) else []:
        print(
            f"- {item.get('filename')} ({item.get('status')}, "
            f"+{item.get('additions', 0)}/-{item.get('deletions', 0)})"
        )
    print()

    print("## PR Commits")
    if not commits:
        print("- none")
    for item in commits if isinstance(commits, list) else []:
        sha = item.get("sha", "")[:7]
        message = item.get("commit", {}).get("message", "").split("\n")[0]
        author = item.get("author", {}).get("login") if isinstance(item.get("author"), dict) else "-"
        print(f"- {sha} {message} ({author or '-'})")
    print()

    print_comment_list("PR Reviews", reviews if isinstance(reviews, list) else [], 40, args.comment_chars)
    print_comment_list(
        "PR Review Comments",
        review_comments if isinstance(review_comments, list) else [],
        args.review_comments_limit,
        args.comment_chars,
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
