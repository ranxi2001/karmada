---
name: e2e-root-cause-analysis
description: Find the root cause of failing or flaky Karmada E2E tests from CI runs. Use when a user reports an e2e test failure, a flaky CI job, or asks to find the root cause of an e2e timeout, providing a GitHub Actions run/job URL, a PR number/URL, or logs.
---

# E2E Root Cause Analysis

Find the root cause of a Karmada E2E failure by working **backwards** from the error you see to the reason behind it. Never stop at the first error message. For each finding, answer: "what does this error mean, and what caused it?" Repeat until you reach a root cause that is fully backed by log evidence.

## Step 0: Find the failing job (if only a PR is given)

If the user gives a PR number or PR URL instead of a job URL, find the failing job first:

```bash
# List all checks of the PR; failing ones come with their job URLs
gh pr checks <pr-number> --repo karmada-io/karmada

# If the failure was on an older commit, list runs for that commit
gh run list --repo karmada-io/karmada --commit <sha> --json databaseId,name,conclusion,url
```

Pick the failing e2e job (e.g. `e2e test (v1.34.0)`) and take its `.../actions/runs/<run_id>/job/<job_id>` URL. If several jobs failed, ask the user which one to look at, or start with the e2e one.

## Step 1: Collect the evidence

Given a GitHub Actions run/job URL (e.g. `.../actions/runs/<run_id>/job/<job_id>`):

1. Audit the run attempt before downloading artifacts:

   ```bash
   python3 <this-skill-dir>/scripts/audit_run_attempt.py <job-url>
   ```

   GitHub exposes artifacts at run scope, and a rerun can replace or obscure the artifacts from the failed attempt. Record the job's `run_attempt`, the run's current attempt, every artifact's `created_at`, and the script's attribution result. Do not use a current-attempt artifact as evidence for an older failed job. Read [references/cross-spec-pollution.md](references/cross-spec-pollution.md) when reruns, shared state, or more than one spec may be involved.

2. Download the job log (the ginkgo output):

   ```bash
   gh api repos/karmada-io/karmada/actions/jobs/<job_id>/logs > job.log
   ```

3. List and download an attempt-compatible, job-matched component-log artifact for the failing job's Kubernetes version. This is the most valuable evidence — it holds the logs of every Karmada component and member cluster:

   ```bash
   gh api repos/karmada-io/karmada/actions/runs/<run_id>/artifacts \
     --jq '.artifacts[] | {id, name}'
   gh run download <run_id> --repo karmada-io/karmada -n karmada_e2e_log_<k8s_version>
   ```

   Artifact layout:
   - `karmada-host/karmada-host-control-plane/containers/` — control-plane components: `karmada-scheduler-*`, `karmada-controller-manager-*`, `karmada-webhook-*`, `karmada-aggregated-apiserver-*`, `karmada-scheduler-estimator-<member>-*`, etc. There are usually two pods per component (leader election); grep both, only the active one has the useful lines.
   - `member3/` — member cluster logs, including `karmada-agent-*` for pull-mode cluster.

## Step 2: Find the failure in the ginkgo log

```bash
grep -n "\[FAILED\]\|Summarizing" job.log
```

For the failing spec, extract:

- The **assertion** that failed (framework helper file:line) and the timeout duration.
- The **Timeline** section: every `STEP:` with its timestamp. Timestamps are the key — they let you match the test's actions against component logs.
- The Timeline of the **previous test case** that shares resources (same CRD, namespace, cluster labels...). Flaky tests are often caused by the previous case's cleanup, which runs in the background and races with the current case's setup.

Warning signs to look for in the timeline:

- A readiness wait (a `framework.Wait*` helper) that passes much faster than normal (milliseconds instead of seconds). This usually means the check read **stale state** left over from the previous case.
- Cleanup steps of the previous case that only wait for the control plane, while changes on the member clusters are still in flight.

When more than one spec may be involved, do not report only object-to-object interactions. Build and prove this causal tuple:

```text
producer spec + source
  -> cleanup hook + source
  -> residual state
  -> consumer spec + source
  -> failed assertion + source
```

Name the exact Ginkgo spec for both producer and consumer. A shared object name, adjacent execution, or plausible lifecycle is not enough to prove cross-spec pollution.

## Step 3: Trace backwards through component logs

Present the analysis in reverse order — from the error you see down to the root cause. At each level, state: *what was seen → what it means → what caused it*. A typical chain:

1. **The test error.** e.g. a timeout while waiting for some object to reach the expected state. Meaning: what the test expected never happened. Question: why?

2. **The decision of the component that owns the object.** Grep that component's log for the object name, e.g.:

   ```bash
   grep -h "<object-name>" karmada-<component>-*.log
   ```

   Depending on the failure, the owning component may be the scheduler (binding never scheduled, `Warning` events explaining why), the controller-manager (work not dispatched, resource not synced to members), the webhook (request rejected), or the agent (pull-mode cluster out of sync). Count how many times the object shows up: if it appears once and never again, the component did **not retry** — see the note below.

3. **Why the component made that decision.** The decision is usually based on some state (cluster status, cache, quota, ...). Grep the logs of the controller that writes that state around the failure window, and build a timeline of those writes with exact timestamps. Compare it with the test's Timeline from Step 2: look for a window in which the state the component read was stale or briefly wrong.

4. **The root cause.** Often a race between test cases: the previous case's cleanup returned after waiting only for the control plane, while changes on the member clusters and status collection were still in flight. State it with the exact timestamps and log lines that prove the window.

If the failing object was expected to recover but never did (e.g. it appears only once in the owning component's log), do not assume the runtime retries on its own — check how retry/requeue actually works in the component's code before claiming "it should self-heal".

## Step 4: Report

Write the conclusion as an evidence chain, from the error backwards:

1. The error seen (assertion, timeout, file:line).
2. What it means (which expected state was never reached).
3. Direct cause with log lines + timestamps (the owning component's decision).
4. Deeper cause (the stale or briefly wrong state, race window with timestamps).
5. Root cause (e.g. cleanup returned too early and did not wait for member clusters to catch up).
6. Why it did not self-heal, if relevant (checked against component code).

Quote exact log lines with timestamps and file names. Check every claim about runtime behavior against the code in the repository (e.g. `pkg/scheduler/`, `pkg/controllers/`) before stating it. Clean up downloaded logs afterwards.

For cross-spec pollution, make the main visual a five-lane timed sequence: producer spec, cleanup code, shared/authoritative state, consumer spec, and assertion. Put timestamps on messages or notes, and label every statement as `[OBS]` (direct log/test evidence), `[CODE]` (source-proven behavior), or `[INFERENCE]` (the causal interpretation). The diagram must answer which test left what state, through which cleanup path, and which later test/assertion observed it. Object-only diagrams may be included as supporting detail, but they are not the primary RCA.

## Step 5: Improve this skill

After the diagnosis is done, review what you learned. If you found something that would help future diagnoses — a new failure pattern, a better command, a log location not listed here, or a wrong assumption in this document — propose an update to this skill file:

- Keep the addition **generic**: describe the pattern, not the specific test, object names, or timestamps of this one case.
- Show the user the proposed change and let them decide whether to apply it.
- Do not commit the change yourself.
