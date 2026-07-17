# Day 26: PR #7697 Targeted Certificate Rotation Fixes

Date: 2026-07-17

## Context

PR [karmada-io/karmada#7697](https://github.com/karmada-io/karmada/pull/7697) adds `karmadactl init --cert-mode=rotate`. A second full review of head `3d1bc25b094f4d93caca37db1384618351e01896` confirmed that the main direction is sound, but found three certificate identity and trust-boundary problems that should be fixed before requesting human approval.

These are ordinary recovery-path risks, not mock-only or deliberately invalid-input cases. They can break API endpoint verification, silently mix credentials between real clusters, or make the control plane unable to reach external etcd after restart.

## Problem 1: Rotation Can Drop Persisted SANs

`buildInitCertConfigs()` reconstructs SANs from the current flags, current control-plane node IPs, and `utils.InternetIP()` on the machine executing rotation. It does not read SANs from the existing leaf certificates.

Concrete failure: installation on machine A automatically records A's public IP in `apiserver.crt`; after expiry, an administrator runs rotation from machine B with all original explicit flags. The renewed certificate can replace A's implicit IP with B's IP. Clients that still use A's endpoint then fail hostname/IP verification after component restart.

The recovery path also becomes dependent on a third-party Internet-IP request even though the old certificate already persists the required identity.

### Fix

- Keep install-time Internet-IP discovery unchanged.
- Build rotation configs without querying the current execution host's Internet IP.
- Merge the existing `karmada.crt` SANs into the renewed karmada certificate config.
- Merge the existing `apiserver.crt` SANs into the renewed apiserver certificate config.
- For internal etcd, merge the existing `etcd-server.crt` SANs before signing the renewed server certificate.
- Treat current explicit flags and topology as additive inputs; never silently remove an existing DNS/IP SAN during renewal.

## Problem 2: CA Equality Is Not Cluster Identity

`refreshLocalAdminKubeconfigIfExists()` currently checks only whether the local kubeconfig CA equals the selected remote `karmada-cert` Secret CA.

Concrete failure: clusters A and B share one enterprise CA but have different `karmada.key` values. Rotation targets B through the host kubeconfig while the default local data path contains A's admin kubeconfig. The CA check passes, A's server URL is retained, and B's renewed `CN=system:admin, O=system:masters` credential is written into that file. Because both clusters trust the same CA and authorize the same subject, the mixed kubeconfig may authenticate successfully instead of failing closed.

### Fix

- Continue checking CA certificate DER equality.
- Load the local kubeconfig client certificate from embedded data or its referenced relative/absolute file.
- Compare its `RawSubjectPublicKeyInfo` with the renewed target `karmada.crt` public key before rewriting the file.
- This identity is stable because rotation intentionally preserves `karmada.key`.
- On mismatch, fail before changing the local file or any Secret.

## Problem 3: External Etcd Contract Allows Credential Replacement

The PR says root CAs are preserved and the first version renews init-managed leaves. However, the external-etcd path accepts arbitrary replacement CA/client files and copies them into Secrets. The current positive test even replaces the old external-etcd CA/client tuple with a different one.

This is a control-plane availability boundary. A wrong external-etcd trust root or client pair takes effect after restart and can disconnect the API server from its data store.

### Fix

Adopt a preserve-only contract for the first version:

- Parse and validate the existing external-etcd CA and client certificate/key pair.
- Preserve the existing Secret bytes on every successful rotation.
- Permit replaying external-etcd file flags only when the supplied files parse to the same existing CA and client certificate identity.
- Reject a different CA or client credential before local or remote mutation, with an error explaining that external-etcd credential rotation is outside `cert-mode=rotate` scope.
- Do not add CA migration, external credential rollout, or automatic restart to this PR.

## Current and Proposed Flow

```text
Current rotate
runCertRotate
  -> build config from current environment
  -> load Secrets and sign leaves
  -> compare local kubeconfig CA only
  -> optionally replace external-etcd credentials
  -> write local kubeconfig, then update Secrets

Proposed rotate
runCertRotate
  -> load existing certificate Secrets
  -> build deterministic rotation config
  -> merge persisted serving-certificate SANs
  -> validate local CA and stable client public key
  -> validate external-etcd files equal existing credentials
  -> write local kubeconfig, then update Secrets
```

## File Scope

| File / area | Change | Reason | Test coverage |
| --- | --- | --- | --- |
| `pkg/karmadactl/cmdinit/kubernetes/deploy.go` | Split the shared config builder internally | Preserve install behavior while omitting execution-host Internet-IP lookup during rotation | Existing install tests and cmdinit package tests |
| `pkg/karmadactl/cmdinit/kubernetes/cert_rotation.go` | Add persisted SAN merge and identity/credential validation | Repair the three certificate and trust-boundary defects | Focused positive, negative, and no-mutation regressions |
| `pkg/karmadactl/cmdinit/kubernetes/deploy_test.go` | Add regressions | Prove the invariants and failure ordering | Focused tests, package tests, full CLI suite |

## Explicit Non-Goals

- No API/config type or generated flag documentation change.
- No CA generation or `pkg/karmadactl/cmdinit/cert` redesign.
- No Secret name, key, or workload template change.
- No CA rotation or `caBundle` migration.
- No automatic workload restart or runtime certificate reload.
- No Helm, operator, cert-manager, or Certificate Framework integration.
- No cross-Secret transaction or rollback state machine in this repair.

## Function Design

- Keep `buildInitCertConfigs()` as the install wrapper. Add a private builder option used only by rotation to omit `InternetIP()`.
- Create rotation configs only after loading the existing `karmada-cert` Secret. Use newly allocated SAN slices and canonical IP strings when merging to avoid aliasing and duplicates.
- Load and merge internal-etcd SANs only after confirming the existing installation is internal etcd.
- Add a kubeconfig certificate loader parallel to the CA loader, supporting embedded and referenced certificate data.
- Reuse parsed-certificate DER/public-key comparisons rather than raw PEM formatting comparisons.
- Parse existing external-etcd client certificate/key bytes as a pair. Supplied client files must also form a valid pair and identify the same certificate.

## Regression Matrix

| Scenario | Expected result |
| --- | --- |
| Old karmada/apiserver SAN exists only in the persisted leaf | Renewed corresponding leaf retains it |
| Old internal-etcd SAN reflects more replicas than current flags | Renewed etcd server leaf retains it |
| Rotation runs from a different/offline machine | No execution-host Internet-IP identity is needed; old SANs remain |
| Local kubeconfig and target share a CA but use different karmada keys | Error; local bytes and all Secrets unchanged |
| Local kubeconfig references a matching relative client certificate file | Identity check succeeds; refreshed credential is embedded as before |
| External-etcd paths replay the existing tuple | Success; existing bytes remain unchanged |
| External-etcd paths provide a different CA or client credential | Error before any mutation |
| Existing external-etcd client certificate/key is malformed or mismatched | Error before any mutation |

## Validation Plan

Run in this order:

1. New focused rotation regressions.
2. `go test ./pkg/karmadactl/cmdinit/... -count=1`.
3. `go test ./pkg/karmadactl/... ./cmd/karmadactl/... ./cmd/kubectl-karmada/... -count=1`.
4. Targeted `golangci-lint` for cmdinit.
5. Command-line flag and import-alias verifiers.
6. `git diff --check` and a final source/diff review.

No push, PR body edit, thread resolution, comment, or reviewer request is authorized by this implementation task.

## Work Log

### 2026-07-17: Design and first implementation pass

- Created this Day 26 record as the only new progress entry for the repair; the previously written Day 13 report was left unchanged.
- Changed only the three files in the scope matrix under `/home/karmada`.
- Kept install-time `InternetIP()` discovery behind the existing `buildInitCertConfigs()` path and disabled it only for rotation.
- Implemented persisted SAN merge for `karmada.crt`, `apiserver.crt`, and internal `etcd-server.crt`.
- Added local kubeconfig client-public-key binding after the existing CA check.
- Changed external etcd from replacement to preserve-only semantics, with parsed certificate and key-pair validation.
- Added focused regressions for SAN preservation, same-CA/different-key kubeconfigs, relative client certificate paths, matching external-etcd flag replay, and rejected external credential replacement.
- Ran `gofmt` and `git diff --check`; both passed.
- Ran the first focused test set: `go test ./pkg/karmadactl/cmdinit/kubernetes -run 'TestCommandInitOption_runCertRotate(PreservesExistingServingCertificateSANs|RefreshesExistingLocalAdminKubeconfig|RejectsLocalAdminKubeconfigFromAnotherCluster|RejectsLocalAdminKubeconfigWithDifferentClientIdentity|WithExistingExternalEtcdCerts|WithExternalEtcdCertFiles|RejectsExternalEtcdCredentialReplacement)$' -count=1`; passed in `59.755s`.

Current status: implementation is local and uncommitted. Broader package/CLI validation and final diff review remain. Nothing has been pushed or posted upstream.

### 2026-07-17: Validation and final local review

Focused and broad validation completed:

- All rotation entry-point tests passed: `go test ./pkg/karmadactl/cmdinit/kubernetes -run '^TestCommandInitOption_runCertRotate' -count=1` (`135.486s`).
- The complete cmdinit suite passed: `go test ./pkg/karmadactl/cmdinit/... -count=1`; `cmdinit/kubernetes` completed in `148.686s`.
- The broad CLI suite passed: `go test ./pkg/karmadactl/... ./cmd/karmadactl/... ./cmd/kubectl-karmada/... -count=1`; `cmdinit/kubernetes` completed in `232.872s` and both CLI command packages exited successfully.
- `hack/verify-command-line-flags.sh` passed with generated docs unchanged.
- `hack/verify-import-aliases.sh` passed.
- Final `git diff --check` passed.

The first lint run found two `gocyclo` failures: `prepareExternalEtcdCertAndKeyData` and `refreshLocalAdminKubeconfigIfExists` both reached complexity 18 with a limit of 15. The repair extracted external-etcd credential consistency checks and local kubeconfig target-identity checks into small contract-specific helpers. After the refactor, `PATH="$(go env GOPATH)/bin:$PATH" golangci-lint run ./pkg/karmadactl/cmdinit/...` passed with `0 issues`. Focused regressions were rerun after the refactor and passed in `43.690s`.

The test helper was then tightened to preserve the original leaf CN, organization, and extended-key usages while changing only key/SAN material. This makes the shared-CA regression model the real `CN=system:admin, O=system:masters` case instead of a weaker synthetic subject. The affected SAN and shared-CA tests passed again in `18.742s`; final lint remained at `0 issues`.

Final source diff in `/home/karmada`:

| File | Additions | Deletions |
| --- | ---: | ---: |
| `pkg/karmadactl/cmdinit/kubernetes/cert_rotation.go` | 159 | 35 |
| `pkg/karmadactl/cmdinit/kubernetes/deploy.go` | 12 | 5 |
| `pkg/karmadactl/cmdinit/kubernetes/deploy_test.go` | 164 | 8 |
| Total | 335 | 48 |

Counterfactual review confirms the new regressions are meaningful against the previous implementation:

- The SAN test would fail because the previous rotation builder never read old leaf SANs.
- The shared-CA/different-key test would fail because the previous guard accepted CA equality and rewrote the kubeconfig.
- The external-etcd replacement tests would fail because the previous implementation accepted and stored a different CA/client tuple.

Final local status: the implementation and validation are complete, but the three source files remain uncommitted on `feature/cert-mode-rotate`. This Day 26 report is untracked on `intern`. No commit, push, PR body edit, thread resolution, comment, or reviewer request has been performed. A live-cluster expiry test was not repeated for this local delta; the prior live test proves the general expiry/restart recovery chain, while the new identity invariants are covered by focused certificate and no-mutation regressions.

### 2026-07-17: Amend and upstream-facing branch update

After the user approved the exact push action, the three-file repair was amended into the existing single signed-off commit on `/home/karmada:feature/cert-mode-rotate`.

- Old head and exact force-with-lease value: `3d1bc25b094f4d93caca37db1384618351e01896`.
- New head: `4328591b02004717e97e40abd537133b1d08f8cf` (`feat: support rotating init-managed certificates`).
- The commit still contains `Signed-off-by: ranxi2001 <ranxi2001@users.noreply.github.com>`.
- Push target: `ranxi2001/karmada:feature/cert-mode-rotate`, which is the upstream-facing head branch for `karmada-io/karmada#7697`.
- Push command used an explicit lease for the old SHA and completed as `3d1bc25b0...4328591b0 (forced update)`.
- No PR body, title, comment, thread, label, or reviewer request was changed.

GitHub post-push verification:

- PR #7697 is open, has one commit, and reports head `4328591b02004717e97e40abd537133b1d08f8cf`.
- The fork branch resolves to the same SHA and the local source worktree is clean.
- DCO completed successfully.
- Fork push workflows started for exact SHA `4328591b0`: CI Workflow `29553109146`, Chart `29553109140`, CLI `29553109182`, and Operator `29553109130`; FOSSA and image-scanning were skipped by workflow rules.
- Upstream PR check runs also started for the same SHA. At the first post-push snapshot, lint/codegen and Kubernetes matrix jobs were queued or in progress with no failures.

Latest status: the source repair is committed and pushed to PR #7697. CI is pending and must be checked again before requesting human review or changing the PR body/threads.
