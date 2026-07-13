---
name: karmada-pr-management
description: >-
  Use when preparing, validating, submitting, updating, or reviewing Karmada
  upstream pull requests: enforce fork/upstream branch hygiene for
  karmada-io/karmada, run fork push CI before upstream PRs, inspect fork branch
  diffs as PR preflight, prepare file-level code-change explanations including
  deleted or extracted code, fill the official PR template, map files to
  OWNERS, choose make test/verify/update commands, disclose AI assistance,
  track review state, read other contributors' PR code before commenting, and
  keep internship notes separate from upstream PR branches.
---

# Karmada PR Management Skill

Use this skill for Karmada upstream PR work: branch prep, fork push CI, pre-PR diff explanation, template filling, issue linking, test selection, OWNERS mapping, review tracking, and update strategy.

## Required Context

- Follow root `AGENTS.md` fork/upstream workflow.
- Upstream PRs must use English.
- Use clean topic branches from `upstream/master`; do not open PRs from `intern`.
- Keep `intern` for internship reports, Chinese notes, local benchmark records, and local skills.
- Do not open an upstream PR, draft PR, WIP PR, issue, upstream review, or upstream comment without explicit user confirmation immediately before posting.
- Prepare the branch, diff, tests, and exact title/body/comment locally first, then ask for approval.
- Prefer fork-only validation before involving `karmada-io/karmada`. Karmada's upstream `.github/workflows/ci.yml` already runs on branch `push` in fork repositories, except `dependabot/**`, so push a topic or validation branch to `origin` and watch the commit SHA Actions/checks. Do not create PRs against the personal fork just to run CI.
- Treat fork branch push CI plus code-change explanation as PR preflight. After pushing a topic branch to `origin` and before opening an upstream PR, inspect the diff, tests, CI state, deleted/extracted code, scope, and reviewer-facing rationale locally.
- Keep internship reports, raw benchmark results, and Chinese-only notes out of upstream PRs unless explicitly intended.
- For other contributors' PRs, do not draft comments or review suggestions until you have read the PR body, changed files, relevant docs/tests, and existing human review discussion.
- For `/kind flake` work, also use `code-review-growth`; its Flake Root-Cause Gate is the canonical evidence and stop policy.
- Prefer script-first PR analysis. If status checks, file summaries, review comment filtering, CI state, or branch hygiene checks are repeated across PRs, improve `.agents/skills/karmada-pr-management/scripts/` and update this skill.

## Upstream Posting Gate

Before any upstream-facing action, stop and ask the user to approve the exact action:

- Creating an upstream PR, including draft or WIP PRs.
- Opening an issue or proposal.
- Posting an issue comment, PR comment, review comment, `/assign`, `/lgtm`, reviewer request, or maintainer mention.
- Pushing to an upstream-facing PR branch when the push will notify reviewers or update an open upstream PR.

Approval request must include:

- Target repo and branch.
- Whether it is upstream-facing or fork-only.
- Title and full body/comment, using the official template when applicable.
- Diff summary and tests run.
- Why upstream attention is needed now.

If the goal is only to run CI, push the branch to the personal fork and inspect the push-triggered GitHub Actions checks. Do not open a self-fork PR.

## Branch Workflow

Expected remotes:

- `origin`: personal fork, usually `https://github.com/ranxi2001/karmada`.
- `upstream`: official project, `https://github.com/karmada-io/karmada.git`.

Add upstream if missing:

```bash
git remote add upstream https://github.com/karmada-io/karmada.git
git fetch upstream master
```

Fork branch roles:

- `origin/master`: clean mirror of `upstream/master` when syncing the fork default branch.
- `origin/intern`: internship reports, local evidence, Chinese notes, local skills, and task tracking.
- Upstream PR topic branches: clean branches from `upstream/master` containing one focused change.

Create a topic branch:

```bash
git fetch upstream master
git switch -c <kind>/<short-topic> upstream/master
```

Examples:

```bash
git switch -c docs/clarify-propagation-policy upstream/master
git switch -c test/scheduler-spread-constraint upstream/master
git switch -c fix/karmadactl-init-validation upstream/master
```

After changes:

```bash
git status
git diff --stat
git commit -s -m "<kind>: <summary>"
git push origin <branch>
```

Do not push to `upstream`.

### Fork Push CI Validation

Karmada differs from repositories where CI is `pull_request`-only: `.github/workflows/ci.yml` explicitly runs on every `push` to upstream/fork repositories except `dependabot/**`. Use this for pre-upstream confidence.

Recommended validation flow:

```bash
git fetch upstream master
git switch -c <kind>/<short-topic> upstream/master
# edit and commit the focused change
git push origin <kind>/<short-topic>:<kind>/<short-topic>
# inspect GitHub Actions for the pushed commit SHA in ranxi2001/karmada
# inspect the local diff while CI runs
git diff --stat upstream/master...HEAD
git diff --name-status upstream/master...HEAD
```

If you need a separate validation branch, use `test/<topic>` or `ci/<topic>` and push it directly:

```bash
git switch -c test/<topic>-validation
git push origin test/<topic>-validation:test/<topic>-validation
```

Do not create a PR against `ranxi2001/karmada` merely to run CI. Push CI success is not enough to open an upstream PR: first prepare the pre-PR diff explanation, including why each changed file exists and whether deleted code was removed, moved, or replaced. If push CI fails, inspect job logs and uploaded artifacts, then classify the failure as a code issue, fork environment difference, missing tag/history difference, CI flake, or upstream-only gate before changing code.

Use `git commit -s` by default for upstream-facing commits. If a commit is missing `Signed-off-by` and the branch is only yours, repair it with `git commit --amend --no-edit --signoff` or `git rebase HEAD~N --signoff`, then update with `git push --force-with-lease`.

## Pre-PR Diff Explanation

Use this workflow after a topic branch is pushed to `origin` and fork CI is running or complete, before opening an upstream PR. This is the local reviewer-readiness step: explain the implementation before asking upstream reviewers to spend attention on it.

Confirm branch base and commit identity:

```bash
git fetch upstream master
git status --short --branch
git log --oneline upstream/master..HEAD
git merge-base --is-ancestor upstream/master HEAD
```

Inspect the implementation shape:

```bash
git diff --stat upstream/master...HEAD
git diff --name-status upstream/master...HEAD
git diff upstream/master...HEAD -- <path>
```

Prepare a local explanation in the internship report, PR draft, or review notes before upstream posting:

- Problem and issue link: what user-visible or maintainer-requested problem the branch addresses.
- Scope and non-goals: what the branch intentionally does not solve.
- File-by-file changes: why each changed file was touched and how it maps to the design.
- Deleted code: state whether it was truly removed, extracted into a new abstraction, renamed, or replaced by existing behavior.
- Behavior compatibility: default path, upgrade impact, feature gate or config impact, and failure modes.
- Tests and evidence: local commands, fork push CI status, commit SHA, and any skipped or blocked checks.
- Reviewer notes: risky areas, open questions, and the exact parts where maintainer feedback is needed.
- Flake evidence when applicable: first hard failure, an `E3` timestamp/code timeline, Mermaid sequence diagram with evidence for every causal arrow, why recovery does not self-heal, the exact invariant introduced, and `E4` counterfactual validation or its explicit limitation.

If this explanation exposes broad unrelated changes, split the branch or reduce scope before opening the PR. If fork CI fails, analyze the failure first and avoid opening a PR only to ask maintainers to debug basic validation.

## PR Planning Checklist

Before editing code:

- Identify issue number or discussion link.
- Check labels, milestone, assignees, `/assign` comments, and linked open PRs; record active ownership as `PR 认领 @`.
- If the issue is actively assigned to someone else, do not start an overlapping PR; choose review/testing feedback or ask whether help is needed.
- Check whether the change touches API types, generated clients, CRDs, Helm charts, operator, CLI, scheduler, controllers, docs, or e2e tests.
- For non-trivial features, run the design-before-code workflow first and keep the planned file scope narrow.
- For `/kind flake`, do not edit synchronization or product logic at `E0-E2`. Reach `E3` in the `code-review-growth` gate first; use `E2` only for diagnostic instrumentation. Seek `E4` before posting, or document why it is impractical and obtain maintainer direction.
- Pick one primary PR kind from the official template:
  - `/kind bug`
  - `/kind feature`
  - `/kind documentation`
  - `/kind cleanup`
- Add optional kinds only when applicable:
  - `/kind api-change`
  - `/kind deprecation`
  - `/kind failing-test`
  - `/kind flake`
  - `/kind regression`
- Prepare a code rationale matrix before opening the upstream PR for feature, API, scheduler, controller, or dependency changes.

## Code Rationale Matrix

Use this local table before opening an upstream PR or asking for maintainer review:

| File / area | Why it changed | Evidence | Test coverage | Reviewer explanation |
| --- | --- | --- | --- | --- |
| `pkg/apis/...` | API field, validation, or type behavior changed | issue, design, compiler/test failure | `make update`, `make verify`, package tests | Explain generated files and compatibility |
| `pkg/controllers/...` | Reconcile behavior changed | failing scenario or source evidence | targeted `go test`, e2e if needed | Explain desired vs observed state |
| `pkg/scheduler/...` | Placement or replica scheduling changed | policy example, test gap | scheduler unit tests, e2e if needed | Explain placement correctness |
| `pkg/karmadactl/...` | CLI behavior changed | command output or validation gap | `go test ./pkg/karmadactl/...` | Explain user-facing behavior |
| `charts/...` | Install values or templates changed | render/install issue | chart verification or install workflow | Explain upgrade impact |

Useful commands:

```bash
python3 .agents/skills/karmada-pr-management/scripts/pr_status.py <pr-number>
git fetch upstream pull/<pr-number>/head:refs/remotes/upstream/pr-<pr-number>
git diff --name-status upstream/master...upstream/pr-<pr-number>
git diff --stat upstream/master...upstream/pr-<pr-number>
git show upstream/pr-<pr-number>:<path> | nl -ba | sed -n '<start>,<end>p'
```

## Test Selection

Use the smallest relevant test set first, then broader checks if needed.

| Change area | Minimum tests |
| --- | --- |
| API types / generated clients / CRDs | `make update` or narrower `hack/update-*.sh`, then `make verify` or narrower `hack/verify-*.sh` |
| Controller logic | `go test ./pkg/controllers/...` or the specific controller package |
| Scheduler logic | `go test ./pkg/scheduler/...` |
| Estimator | `go test ./pkg/estimator/... ./cmd/scheduler-estimator/...` |
| CLI / `karmadactl` | `go test ./pkg/karmadactl/... ./cmd/karmadactl/... ./cmd/kubectl-karmada/...` |
| Operator | `go test ./operator/...` |
| Aggregated API server / search / metrics | targeted package tests under `pkg/` and `cmd/` |
| Flake fix | controlled reproduction or focused regression for the proven causal edge, plus the directly affected package/e2e tests |
| Helm chart | render/install verification through chart workflow or local Helm command if available |
| Docs only | link/context check plus no code tests unless docs include generated output |
| Broad Go change | `make test` |
| Repository-wide generated/static checks | `make verify` |

If a test cannot run locally, record the command and exact blocker.

## Generated Code and Verification

Karmada has many generated artifacts. Before claiming a change is ready:

- For API, CRD, client, OpenAPI, command flag, mock, lifted, import alias, vendor, or estimator protobuf changes, identify the relevant `hack/update-*.sh` and `hack/verify-*.sh` scripts.
- Do not run update/generator targets concurrently in the same worktree.
- After generation, inspect the diff and explain generated files in the PR.
- If `make verify` fails, classify whether it is caused by the PR, missing local tooling, environment, or pre-existing repository state.

## Read-Before-Reply Workflow For Existing PRs

Use this workflow before analyzing, reviewing, replying to, or building on someone else's PR.

1. Read the PR body and identify scope, linked issues, PR kind, author, assignees, reviewers, labels, CI state, and merge-gate state.
2. Read proposal or design docs if the PR adds one.
3. Read `Files changed`, not only the conversation. Inspect implementation, API/CRD changes, generated files, tests, charts, and docs touched by the PR.
4. Read human review comments and author replies before bot comments.
5. Check whether later commits already addressed an earlier review comment.
6. Compare the proposed comment against the current PR text/code.
7. For a flake PR, independently verify the code-backed causal timeline, retry/requeue path, recovery event, and patch counterfactual; green CI alone is not a correctness argument.
8. Record evidence locally before posting: PR number, commit SHA, files/sections read, key observations, unresolved questions, and comment purpose.

Useful commands:

```bash
git fetch upstream pull/<pr-number>/head:refs/remotes/upstream/pr-<pr-number>
git show --stat --oneline upstream/pr-<pr-number>
git diff upstream/master...upstream/pr-<pr-number> -- <path>
python3 .agents/skills/karmada-pr-management/scripts/pr_status.py <pr-number>
python3 .agents/skills/karmada-issue-discussion/scripts/thread_brief.py <pr-number>
```

### High-Risk Differential Review

Use this focused pass when a PR removes or weakens behavior around certificates/private keys, authentication/validation, scheduler retry/queue/`Forget`/event predicates, controller cleanup/finalizers/idempotence, or API defaults/compatibility. Do not apply it to ordinary mechanical changes.

1. Read both base and head implementations. When an old guard or branch disappears, use `git log -S'<symbol-or-condition>' -- <path>` and `git blame <base> -- <path>` to learn why it existed.
2. Build a lightweight effect ledger: inputs and trust source; API/cache/status/Secret/file reads; object/status/queue/file/certificate writes; direct callers and asynchronous consumers; preserved invariants; unresolved uncertainty.
3. Map semantic blast radius as an effect graph: changed function -> callers -> shared state/cache -> watches or predicates -> queue/retry -> affected resources/components -> recovery and rollout path. Do not use caller, file, or line counts as risk thresholds.
4. Review tests as behavioral claims. Ask whether each regression would fail with the patch reverted and whether recovery, mixed-version, negative, and boundary paths are covered.
5. Disclose coverage: areas deep-reviewed, surface-scanned, generated or low-risk areas skipped, evidence confidence, and residual unknowns.
6. Label output as `blocking`, `non-blocking`, `question`, or `evidence gap`. For non-obvious conclusions, use the independent falsification pass from `code-review-growth` before posting.

## OWNERS Mapping

Use `OWNERS` by changed path:

| Path | OWNER file |
| --- | --- |
| `pkg/apis/` | `pkg/apis/OWNERS` |
| `pkg/controllers/` | `pkg/controllers/OWNERS` |
| `pkg/scheduler/` | `pkg/scheduler/OWNERS` |
| `pkg/estimator/` | `pkg/estimator/OWNERS` |
| `pkg/karmadactl/` | `pkg/karmadactl/OWNERS` |
| `pkg/resourceinterpreter/` | `pkg/resourceinterpreter/OWNERS` |
| `pkg/aggregatedapiserver/` | `pkg/aggregatedapiserver/OWNERS` |
| `operator/` | `operator/OWNERS` |
| `charts/` | `charts/OWNERS` |
| `cmd/` | `cmd/OWNERS` plus narrower `cmd/*/OWNERS` if present |
| `docs/` | `docs/OWNERS` |
| `.github/` | `.github/OWNERS` |
| `test/` | `test/OWNERS` |
| `hack/` | `hack/OWNERS` |

Let the bot guide exact approval requirements; do not over-tag reviewers unless needed.

## PR Template

Always use `.github/PULL_REQUEST_TEMPLATE.md` exactly as the base for upstream PRs, including draft and WIP PRs.

````md
**What type of PR is this?**

/kind documentation

**What this PR does / why we need it**:

<problem and change summary>

**Which issue(s) this PR fixes**:

Fixes #<issue>

**Special notes for your reviewer**:

- Scope:
- Implementation notes:
- Tests:
- AI assistance: Used Codex to help inspect code, draft tests, and prepare this PR. I reviewed and validated the changes.

**Does this PR introduce a user-facing change?**:

```release-note
NONE
```
````

For partial work use `Part of #<issue>` or `Refs #<issue>` instead of `Fixes #<issue>`.

If a PR is intentionally unfinished, use `[WIP]` in the title and still get user approval before creation. Prefer fork branch push CI for WIP validation unless upstream maintainers explicitly need to see the work.

## Review Management

When review comments arrive:

1. Read all comments first.
2. Classify commenters by role: human maintainer/reviewer, PR author, contributor, automation bot, CI bot, merge gate, or AI reviewer.
3. Group actionable comments by category: correctness, tests, style, docs, generated code, scope.
4. Prioritize human maintainer/reviewer comments; validate AI reviewer comments yourself before acting.
5. Treat bot comments as process or validation state.
6. For a flake review, do not recommend `/lgtm` or `/approve` until the causal chain and the edge cut by the patch are source-proven; success across CI matrices does not replace RCA.
7. Decide whether each fix belongs in the current PR, a temporary validation branch, or a separate PR from `upstream/master`.
8. Apply fixes locally, validate, then update the PR with a clean history.
9. Reply directly and specifically after user approval when the reply is upstream-facing.

Useful response format:

```md
Thanks, updated in the latest push.

Change:
- ...

Validation:
- ...
```

## PR Status Script

Use the scripts to inspect a PR:

```bash
python3 .agents/skills/karmada-pr-management/scripts/pr_status.py <pr-number>
python3 .agents/skills/karmada-issue-discussion/scripts/thread_brief.py <pr-number>
```

`pr_status.py` prints title, state, labels, files, commits, comments count, and review comments summary. `thread_brief.py` gives broader discussion context.

## Guardrails

- Do not create upstream PRs, draft PRs, WIP PRs, issues, or comments without immediate user approval of the exact title/body/comment.
- Do not use upstream PRs as disposable CI runners.
- Do not create self-fork PRs just to run CI; use Karmada's existing push-triggered fork CI.
- Do not open an upstream PR before fork push CI state and pre-PR diff explanation are prepared locally.
- Do not treat fork push CI success as sufficient PR readiness without explaining file-level changes, deleted code, tests, and residual risk.
- Do not open or endorse a flake fix whose rationale stops at rerun success, timing correlation, or a generic wait. Require the `code-review-growth` `E3` causal timeline and an invariant-specific patch.
- Do not ignore the official PR template.
- Do not comment on or mention maintainers in read-only PR analysis unless the user approves and upstream input is genuinely needed.
- Do not merge unrelated formatting with behavior changes.
- Do not leave deleted code unexplained; identify whether it was removed, moved, extracted, renamed, or replaced.
- Change as few files as needed for the stated problem.
- Do not include code cleanliness, formatting, dependency tidying, comment polishing, or unrelated refactors just because they look safe.
- Do not add new dependencies casually.
- Do not change API/CRD behavior without generated files and compatibility notes.
- Do not mark an issue fixed unless the PR fully addresses it.
- Do not duplicate work on an issue with an active assignee or open PR; record `PR 认领 @` and switch to review/test feedback unless maintainers ask for a separate PR.
- Do not treat AI reviewer or automation bot comments as maintainer consensus.
