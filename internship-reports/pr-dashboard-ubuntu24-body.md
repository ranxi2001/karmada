**What type of PR is this?**

/kind cleanup

**What this PR does / why we need it**:

This PR updates GitHub-hosted Ubuntu runners from `ubuntu-22.04` to `ubuntu-24.04` across the workflow files under `.github/workflows`.

This follows up on karmada-io/karmada#7728 and the same GitHub Actions runner-images deprecation notice for `ubuntu-22.04`:

https://github.com/actions/runner-images/issues/14254

`ubuntu-24.04` is the current GA Ubuntu runner image, while `ubuntu-26.04` is still in preview. This keeps the dashboard workflows on a fixed Ubuntu runner label instead of switching to `ubuntu-latest`.

**Which issue(s) this PR fixes**:

None

**Special notes for your reviewer**:

Changed files:

- Updated all `runs-on: ubuntu-22.04` labels under `.github/workflows` to `runs-on: ubuntu-24.04`.
- No workflow logic, job matrix, action version, script, or test command was changed.

Validation:

- `git grep -n "ubuntu-22.04" HEAD -- .github/workflows || true`
- `git diff --check upstream/main...HEAD`
- Parsed all `.github/workflows/*.yml` and `.github/workflows/*.yaml` with Python `yaml.safe_load`

Fork push CI on `ranxi2001/dashboard:chore/update-github-runner-ubuntu-24`, commit `8f6ba046914e3e1bcc3a4d94f33912c10e33c64f`:

- `CI Workflow`: passed, including lint, unit test, build-bin, build-frontend, and e2e-frontend tests on Kubernetes v1.33.0, v1.34.0, and v1.35.0

This PR was prepared with AI assistance.

**Does this PR introduce a user-facing change?**:

```release-note
NONE
```
