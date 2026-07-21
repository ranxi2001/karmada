# Repository Guidelines

## Project Structure

Karmada is a Go-first Kubernetes multi-cluster orchestration project. Main binaries live under `cmd/`, including `karmada-controller-manager`, `karmada-scheduler`, `karmada-agent`, `karmada-aggregated-apiserver`, `karmada-webhook`, `karmada-descheduler`, `karmada-search`, `karmada-metrics-adapter`, `karmadactl`, and `kubectl-karmada`. Shared implementation packages live under `pkg/`; API types are under `pkg/apis/`; generated clients and informers are under `pkg/generated/`. The operator lives in `operator/`. Helm charts are under `charts/`. Local deployment, generation, and verification scripts are in `hack/`. End-to-end tests are under `test/e2e/`, with helper code in `test/helper/`.

## Build, Test, and Development Commands

- `make all`: builds all Karmada binaries listed in the root `Makefile`.
- `make karmadactl` / `make kubectl-karmada`: builds the CLI binaries.
- `make karmada-controller-manager`: builds one component for a focused loop.
- `make test`: runs race-enabled Go tests for `pkg/...`, `cmd/...`, `examples/...`, and `operator/...`, with coverage output in `_output/coverage/`.
- `make verify`: runs repository verification scripts through `hack/verify-all.sh`.
- `make update`: regenerates generated artifacts through `hack/update-all.sh`.
- `hack/local-up-karmada.sh`: creates a local Karmada environment with a host cluster, control plane, and member clusters.
- `make clean`: removes `_tmp` and `_output`.

This repository currently uses Go `1.26.4`, as declared in `go.mod` and `.go-version`.

## Coding Style and Tests

Use standard Go formatting and local Kubernetes controller patterns. API type changes usually require updating generated code and verification artifacts; run `make update` or the narrower script only after confirming the relevant API boundary. Add unit tests near changed packages, especially for scheduler decisions, controller reconcile logic, API validation, CLI behavior, and status aggregation. Use e2e tests for install, propagation, failover, multi-cluster scheduling, operator, and CLI workflows that cannot be proven with unit tests.

## Internship Report Guidelines

Keep internship records on the `intern` branch unless the user explicitly asks otherwise. Do not mix Chinese learning notes, local-only skills, benchmark logs, or task tracking into upstream-facing topic branches.

Use these files for local learning state:

- `PROGRESS.md`: short loop memory only. Read it at the start of each work loop and update it at the end with last work, blockers, ruled-out paths, next step, and stop conditions.
- `internship-reports/`: daily reports, architecture notes, source-reading records, benchmark notes, community triage notes, and mentor-facing summaries.
- `internship-reports/todo.md`: current task inventory with status, priority, evidence, and next action.
- `internship-reports/intern-glossary.md`: recurring Karmada, Kubernetes, multi-cluster, scheduler, and controller terms.
- `.agents/skills/`: reusable workflows that are useful enough to repeat across projects or later Karmada tasks.

When writing learning reports, include process blockers and debugging evidence, not just the final successful path. Record failed commands, observed errors, likely root causes, and workarounds. For abstract Kubernetes or distributed-systems concepts, add short Markdown notes such as `> 注释：...` or `> 分析：...` near the relevant paragraph so a future reviewer can read the report without chat context.

Write the majority of internship-report prose and headings in Chinese. Preserve exact code identifiers, API fields, commands, errors, upstream titles, links, and short source quotations in their original language. For API design, controller/scheduler flow, RCA, concurrency, lifecycle, or any explanation involving three or more dependent steps, put a `## 先说人话` or `## 通俗解释` section near the beginning. Explain the outcome with one concrete example before presenting source paths, field matrices, or implementation jargon. Use the order `结论 -> 具体例子 -> 运行过程 -> 技术证据 -> 未决边界 -> 下一步`, and use `.agents/skills/explain-technical-content/` for this comprehension pass.

When preparing long reusable text such as upstream issue comments, PR descriptions, review comments, mentor summaries, or Mermaid explanations, write it into the appropriate report or draft file instead of only returning it in terminal/chat output. The terminal is inconvenient for copying and should not be the only handoff surface for content the user is expected to reuse.

Treat upstream reviewer-facing text as an index, not as the full internship report. For ordinary PR bodies and comments, keep the problem, behavior, material risk, validation, and requested action within one screen when practical; leave file tables, complete test matrices, chronological debugging logs, dynamic CI status, and full RCA/proposal evidence in a stable linked issue, proposal, or local report. Apply the concise-first gates in `karmada-pr-management` and `karmada-issue-discussion`, and explicitly justify long-form exceptions.

When scanning issues or choosing review targets, apply production relevance before deep analysis. Do not spend substantial tokens or recommend implementation for mock-only failures, deliberately invalid inputs, manually constructed impossible state, or extreme scheduler/configuration cases without evidence that normal production workflows reach them. Treat a framework-recovered panic, self-healing reconcile, or validation error improvement as low-value hygiene when the patch does not improve the final system outcome. Exceptions require material security, data-loss, process-wide availability, compatibility impact, repeated real incidents, or explicit maintainer direction. It is valid to report that no worthwhile candidate exists. Prefer fixes at an existing contract or ownership boundary; avoid adding nested defensive branches merely because a mock can exercise them. This gate allocates our attention; it is not by itself a reason to discourage or block another contributor's small correct patch. Upstream objections still need a concrete complexity, correctness, contract, or impact-claim problem; lack of a company incident alone is not a blocker.

When creating diagrams or other visual artifacts for reports, do not wait for the user to ask for a preview. Deliver a directly viewable PNG or SVG alongside the editable source (`.drawio`, Mermaid, etc.) by default. If the preferred export tool is unavailable, proactively use a reasonable fallback such as Mermaid rendering or a local script-generated PNG, and record the tool limitation in the report or `PROGRESS.md`.

When `.drawio` and `.mmd` coexist, record which source and renderer produced each PNG/SVG and designate the canonical source. Do not call independently authored files equivalent or synchronized. Curated parallel views are acceptable when separate layouts materially improve clarity, but audit their key components, relations, and invariants after changes; evaluate visual clarity separately from source-maintenance quality.

Use `.agents/skills/project-mermaid/` for project data-flow, event-flow, lifecycle, and sequence diagrams whose canonical source should be `.mmd` with a generated PNG/SVG. Use `.agents/skills/drawio-skill/` for architecture, topology, vendor-icon, swimlane, and precise custom-layout diagrams. Choose by the question and required deliverable, not by which tool was used previously.

Use `.agents/skills/youtube-transcript-proofread/` for Karmada YouTube meeting evidence. Confirm each video's exact title and total duration before stating coverage; keep raw ASR, Agent-corrected transcript, and paraphrased meeting digest as separate artifacts; validate SRT timestamps against media duration; and do not infer named speakers or maintainer consensus without an official transcript or explicit meeting evidence.

Use English for every newly created diagram or visual artifact in this Karmada workspace, including images stored only in internship reports, because they may later be reused in upstream issues, PRs, reviews, or community meetings. Do not generate Chinese-labeled diagrams unless the user explicitly requests a local-only Chinese learning artifact. Any upstream- or community-facing image must be English-only.

Name report images and exported visual assets in `internship-reports/` with a `dayN-` prefix matching the report that uses them, and update both local Markdown links and raw GitHub image URLs when renaming.

On the current Windows workspace only, draw.io is installed per-user at `C:\Users\ranxi\AppData\Local\Programs\draw.io\draw.io.exe` and is not on PATH. For drawio-skill exports on this Windows machine, use this full path before declaring draw.io unavailable; `drawio`, `draw.io`, and `C:\Program Files\draw.io\draw.io.exe` may fail even when the app is installed. On macOS or other machines, follow the normal drawio-skill detection order instead of assuming this Windows path.

The repo-local `.agents/skills/drawio-skill/` is a Codex-adapted runtime vendor of `Agents365-ai/drawio-skill`. Upgrade it only from a verified stable release tag, record the tag and commit in `PROGRESS.md` or an internship report, preserve its MIT license and local `agents/openai.yaml`, and do not copy or enable upstream GitHub Actions as part of a runtime-only upgrade.

## Knowledge Capture Rules

At the end of each task, classify useful outcomes before stopping:

- Stable repo conventions, user preferences, environment facts, and repeated constraints go into `AGENTS.md`.
- Temporary state that helps the next few runs goes into `PROGRESS.md`.
- Evidence, source-reading notes, debugging process, benchmark context, and mentor-facing records go into `internship-reports/`.
- Repeatable workflows with five or more steps go into `.agents/skills/<skill-name>/SKILL.md`.
- Plain-language explanations and Chinese report readability use `.agents/skills/explain-technical-content/`.
- Code review workflows and reusable missed-review lessons go into `.agents/skills/code-review-growth/`; use it when reviewing PRs or analyzing maintainer review comments.

Do not store raw chat history. Keep conclusions concise, cite file paths or command evidence when useful, and replace outdated rules instead of letting contradictory notes accumulate.

## Fork and Upstream Workflow

This workspace currently has `origin` configured as the personal fork: `https://github.com/ranxi2001/karmada`. Add an `upstream` remote for `https://github.com/karmada-io/karmada.git` before doing upstream sync or official PR work.

Keep `intern` for internship notes and learning assets. For upstream-facing changes, create a clean topic branch from the latest upstream `master`, include one focused change, run the relevant verification commands, and keep internship records out of the PR branch. Before opening an upstream PR, issue, review comment, maintainer mention, or community-facing proposal, get explicit user confirmation on the exact target and English text.

Do not create PRs against the personal fork just to run CI. Karmada's `.github/workflows/ci.yml` already runs on `push` to fork branches, except `dependabot/**`, and on `pull_request`. For pre-upstream validation, push the topic or validation branch to `origin` and watch the commit SHA Actions/checks directly. If a push-triggered fork CI failure differs from upstream PR CI, classify it as code issue, fork environment difference, or CI flake before changing code.

## Security and Configuration

Do not commit real kubeconfigs, cloud credentials, registry credentials, tokens, or private cluster details. If local secrets are needed for experiments, keep them in ignored files with restricted permissions and never paste values into reports, logs, commits, or PR text.
