**What type of PR is this?**

/kind cleanup

**What this PR does / why we need it**:

This PR updates GitHub-hosted Ubuntu runners from `ubuntu-22.04` to `ubuntu-24.04` across the workflow files under `.github/workflows`.

GitHub Actions runner-images has announced that `ubuntu-22.04` will begin deprecation on September 17, 2026 and become fully unsupported on April 17, 2027:

https://github.com/actions/runner-images/issues/14254

`ubuntu-24.04` is the current GA Ubuntu runner image, while `ubuntu-26.04` is still in preview. This keeps Karmada on a fixed Ubuntu runner label instead of switching to `ubuntu-latest`, so workflow environments remain explicit and predictable.

This follows the same repository-wide runner image update pattern as #3699.

**Which issue(s) this PR fixes**:

None

**Special notes for your reviewer**:

Changed files:

- Updated all `runs-on: ubuntu-22.04` labels under `.github/workflows` to `runs-on: ubuntu-24.04`.
- No workflow logic, job matrix, action version, script, or test command was changed.

Validation:

- `git grep -n "ubuntu-22.04" HEAD -- .github/workflows || true`
- `git diff --check upstream/master...HEAD`
- Parsed all `.github/workflows/*.yml` and `.github/workflows/*.yaml` with Python `yaml.safe_load`

Fork push CI on `ranxi2001/karmada:chore/update-github-runner-ubuntu-24`, implementation commit `0f62fd62b05802961447601da9000403139b600d`:

- `CI Workflow`: passed, including lint, codegen, compile, unit test, and e2e tests on Kubernetes v1.34.0, v1.35.0, and v1.36.1
- `Chart`: passed on Kubernetes v1.34.0, v1.35.0, and v1.36.1
- `CLI`: passed on Kubernetes v1.34.0, v1.35.0, and v1.36.1
- `Operator`: passed on Kubernetes v1.34.0, v1.35.0, and v1.36.1
- `FOSSA`: skipped by workflow condition
- `image-scanning`: skipped by workflow condition

The latest PR head `de3b6be675bbf8ad12f91052f7d0fb53c5b592a5` is a signed-off empty commit used only to retrigger pull request CI after an isolated e2e failure; it does not change the diff.

This PR was prepared with AI assistance.

**Does this PR introduce a user-facing change?**:

```release-note
NONE
```
