---
name: karmada-push-ci-check
description: Check GitHub Actions push CI for Karmada fork branches and commits when the user explicitly asks for a fork CI check or an observed fork-specific failure needs diagnosis. Use to verify a requested fork run, summarize workflow status, poll Actions runs, or inspect failed jobs; do not use as a default upstream PR gate or PR-body evidence.
---

# Karmada Push CI Check

## Overview

Use this skill to check GitHub Actions runs on a Karmada fork branch from the CLI only when the user explicitly requests that check or a known fork-specific failure needs diagnosis. Do not invoke it as a default prerequisite for opening or updating an upstream PR, and do not cite its result in a PR body unless the user asks.

## Quick Start

From a Karmada worktree:

```bash
python3 /home/karmada/.agents/skills/karmada-push-ci-check/scripts/check_push_ci.py \
  --repo ranxi2001/karmada \
  --branch "$(git rev-parse --abbrev-ref HEAD)" \
  --sha "$(git rev-parse HEAD)"
```

Watch until all matching runs finish:

```bash
python3 /home/karmada/.agents/skills/karmada-push-ci-check/scripts/check_push_ci.py \
  --repo ranxi2001/karmada \
  --branch feature/cert-manager-layout \
  --watch --interval 60
```

Show failed job details for terminal failures:

```bash
python3 /home/karmada/.agents/skills/karmada-push-ci-check/scripts/check_push_ci.py \
  --repo ranxi2001/karmada \
  --branch feature/cert-manager-layout \
  --sha "$(git rev-parse HEAD)" \
  --show-jobs failed
```

## Workflow

1. Before checking CI, make sure the fork branch contains the commit that should be tested. If the branch was rebased or amended, push with `git push --force-with-lease origin <branch>:<branch>`.
2. Run `scripts/check_push_ci.py` with the fork repo, branch, and expected HEAD SHA.
3. Treat `success`, `skipped`, and `neutral` as non-failing conclusions.
4. Treat `failure`, `timed_out`, `cancelled`, `startup_failure`, and `action_required` as failing conclusions.
5. Treat `queued`, `requested`, `waiting`, `pending`, and `in_progress` as pending status.
6. If runs are pending, use `--watch` or rerun the command later.
7. If a workflow failed, rerun with `--show-jobs failed` to print failed job URLs and step names.

## Notes

- The script uses the public GitHub REST API and does not require `gh auth login`.
- Set `GH_TOKEN` or `GITHUB_TOKEN` when unauthenticated rate limits are too low.
- Exit code `0` means all matching runs are complete and non-failing.
- Exit code `1` means at least one matching run failed.
- Exit code `2` means at least one matching run is still queued or running.
- Exit code `3` means no matching Actions runs were found.
