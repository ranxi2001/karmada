---
name: open-source-onboarding
description: Set up and maintain a practical onboarding workspace for learning an open-source repository. Use when Codex needs to create or update internship-style learning records, repo-specific AGENTS.md rules, short PROGRESS.md loop memory, TODO tracking, glossary files, daily reports, source-reading plans, first-week study plans, or reusable documentation workflows for a new OSS project.
---

# Open Source Onboarding

## Overview

Create a lightweight learning system around an existing repository without polluting upstream-facing code. Preserve repo-specific facts, keep temporary state short, and turn repeated onboarding or review routines into reusable skills.

## Workflow

1. Inspect the repository before writing.
   - Read `README*`, `CONTRIBUTING*`, `go.mod`/package manifests, root `Makefile` or build scripts, `docs/`, `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE*`, `OWNERS`, and the top-level directory layout.
   - Check `git status --short --branch` and `git remote -v`.
   - Identify the default upstream branch and personal fork branch if possible.

2. Create or update the local learning structure.
   - Put durable agent rules in root `AGENTS.md`.
   - Put short loop memory in root `PROGRESS.md`.
   - Put learning reports under `internship-reports/`.
   - Put task inventory in `internship-reports/todo.md`.
   - Put recurring terminology in `internship-reports/intern-glossary.md`.
   - Put reusable workflows under `.agents/skills/<skill-name>/SKILL.md`.

3. Keep upstream and learning work separate.
   - Preserve the upstream README unless the user explicitly asks for a local navigation page.
   - Keep notes, Chinese learning docs, local benchmark logs, and local skills on an `intern` or equivalent learning branch.
   - For upstream PRs, create a clean topic branch from the latest upstream default branch and include only one focused change.

4. Write reports as evidence trails.
   - Write most local report prose and headings in the user's preferred language; in this Karmada workspace, default to Chinese.
   - For complex API, controller, scheduler, RCA, concurrency, or lifecycle analysis, use `$explain-technical-content` and put a plain-language section before the evidence inventory.
   - Lead with one concrete example, then explain component roles and state flow before listing symbols or file paths.
   - Record failed commands, errors, root-cause hypotheses, workarounds, and final resolution.
   - Separate local measured data, upstream official facts, and engineering inference.
   - When studying a review thread, record the decision method as well as the outcome: prior-art relevance, numbered event sequence, option tradeoffs, and the boundary between problem confirmation and solution approval.
   - Add short explanatory blockquotes for concepts that a future reviewer may not know.

5. End each work loop with classification.
   - Stable rules and environment facts: `AGENTS.md`.
   - Short next-run state: `PROGRESS.md`.
   - Evidence and long-form reasoning: `internship-reports/`.
   - Current task state: `internship-reports/todo.md`.
   - Repeatable multi-step routines: `.agents/skills/`.

## Initial File Set

Use this minimum set unless the repository already has equivalents:

- Root `AGENTS.md`
  - Project structure and important directories.
  - Build, test, and verification commands.
  - Report-writing rules.
  - Fork/upstream branch hygiene.
  - Security and secret-handling rules.
- Root `PROGRESS.md`
  - Goal.
  - Last run.
  - Current blockers.
  - Ruled-out paths.
  - Next steps.
  - Stop conditions.
- `internship-reports/README.md`
  - Purpose of the report directory.
  - Links to TODO and glossary.
  - Report-writing checklist.
- `internship-reports/todo.md`
  - Current priority table.
  - First-week suggested plan.
  - Blocker template.
  - Completed milestones.
- `internship-reports/intern-glossary.md`
  - Layered glossary from beginner concepts to project-specific architecture.
  - Common confusing term pairs.
  - Rules for when to add terms.

For concrete Markdown skeletons, read `references/report-templates.md`.

## First-Week Planning

Build a first-week plan around evidence, not just reading:

1. Day 1: Read official quick start and run or preflight the local setup.
2. Day 2: Map the repository structure and technology stack.
3. Day 3: Trace one real user workflow from sample input to runtime effect.
4. Day 4: Deep-read the first core subsystem and its tests.
5. Day 5: Deep-read the second core subsystem and its tests.
6. Day 6: Triage open issues/PRs and find a low-risk contribution.
7. Day 7: Write a weekly summary focused on reusable engineering judgment.

Adjust subsystem choices to the project. For Kubernetes projects, common tracks are API types, controller reconcile loops, scheduler logic, CLI, operator, charts, and e2e tests.

## Writing Standards

- Prefer concise, source-grounded notes over generic summaries.
- Optimize first for reader comprehension, then for evidence density. A technically correct report is incomplete when its conclusion requires private chat context or unexplained jargon.
- Keep local daily reports mostly in Chinese while preserving exact technical identifiers and source quotations in English.
- Use `结论 -> 具体例子 -> 运行过程 -> 技术证据 -> 未决边界 -> 下一步` for complex reports unless an established local template is clearer.
- Keep `PROGRESS.md` short; do not duplicate daily reports there.
- Do not paste secrets, private kubeconfigs, tokens, or raw chat history.
- Do not create a new daily report too early when continuing the same investigation; extend the existing report until it becomes substantial.
- Preserve upstream contribution language in English unless the project explicitly accepts another language.
- Ask for explicit user confirmation before upstream-facing PRs, issues, comments, reviewer requests, maintainer mentions, or proposal publication.

## Validation

After creating or updating a skill, run the skill validator if available. For repository docs, run `git status --short` and inspect the diff to confirm only learning/report files changed unless the user requested code edits.
