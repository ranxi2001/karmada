# Day 33 `karmadactl top` Flake Upstream Draft

## Target

- Repository: `karmada-io/karmada`
- Base: `master`
- Head: `ranxi2001:test/karmadactl-top-stable-pod`
- Local commit: `14b24b90db739a3091f6d1877c598a9f7f696e3d`
- Status: published as [`karmada-io/karmada#7795`](https://github.com/karmada-io/karmada/pull/7795)

## Title

```text
test(e2e): stabilize karmadactl top pod fixture
```

## Body

````markdown
**What type of PR is this?**

/kind flake

**What this PR does / why we need it**:

The `Karmadactl top existing pod` E2E uses an nginx and busybox Pod on each member cluster. The busybox container has no long-running command, so it exits and restarts while the test moves from its one-time PodMetrics readiness checks to the later sequential `karmadactl top` queries. Metrics can therefore be observed as ready and then return `PodMetrics NotFound` during the real assertion.

This change keeps busybox running only in this test context. It also verifies that the Pod UID and container IDs remain unchanged, with every container Ready, Running, and at zero restarts, from metrics readiness through all existing `top` queries. Shared fixtures and `karmadactl` behavior are unchanged.

**Which issue(s) this PR fixes**:

Part of #6841

**Special notes for your reviewer**:

- Focused two-member Kubernetes v1.36.1 E2E: fixed and restored variants passed; removing only the busybox command failed the lifecycle assertion after PodMetrics readiness succeeded.
- `go test ./test/e2e/suites/base -run '^$' -count=0`
- AI assistance: Codex helped analyze the CI failure, implement the test fix, and prepare validation; I reviewed the code and results.

**Does this PR introduce a user-facing change?**:

```release-note
NONE
```
````

## Publication Result

1. `upstream/master` remained `eb2e7c75ff828afbb34f625a105a24f5a973c1cc`; no rebase was required.
2. #6841 remained open with no assignee; no open PR matched the exact spec, error, or changed file.
3. Package compile, `gofmt`, `git diff --check`, one-file scope, DCO, and 200-word body gates passed.
4. After user confirmation, the topic branch was pushed and the exact title/body above was published as #7795. GitHub added only a trailing newline to the body.
