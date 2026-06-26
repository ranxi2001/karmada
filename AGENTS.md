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

## Knowledge Capture Rules

At the end of each task, classify useful outcomes before stopping:

- Stable repo conventions, user preferences, environment facts, and repeated constraints go into `AGENTS.md`.
- Temporary state that helps the next few runs goes into `PROGRESS.md`.
- Evidence, source-reading notes, debugging process, benchmark context, and mentor-facing records go into `internship-reports/`.
- Repeatable workflows with five or more steps go into `.agents/skills/<skill-name>/SKILL.md`.

Do not store raw chat history. Keep conclusions concise, cite file paths or command evidence when useful, and replace outdated rules instead of letting contradictory notes accumulate.

## Fork and Upstream Workflow

This workspace currently has `origin` configured as the personal fork: `https://github.com/ranxi2001/karmada`. Add an `upstream` remote for `https://github.com/karmada-io/karmada.git` before doing upstream sync or official PR work.

Keep `intern` for internship notes and learning assets. For upstream-facing changes, create a clean topic branch from the latest upstream `master`, include one focused change, run the relevant verification commands, and keep internship records out of the PR branch. Before opening an upstream PR, issue, review comment, maintainer mention, or community-facing proposal, get explicit user confirmation on the exact target and English text.

## Security and Configuration

Do not commit real kubeconfigs, cloud credentials, registry credentials, tokens, or private cluster details. If local secrets are needed for experiments, keep them in ignored files with restricted permissions and never paste values into reports, logs, commits, or PR text.
