**What type of PR is this?**

/kind cleanup

**What this PR does / why we need it**:

This PR updates GitHub-hosted Ubuntu runners from `ubuntu-22.04` to `ubuntu-24.04` in the website workflow files.

This follows up on karmada-io/karmada#7728 and the same GitHub Actions runner-images deprecation notice for `ubuntu-22.04`:

https://github.com/actions/runner-images/issues/14254

`ubuntu-24.04` is the current GA Ubuntu runner image, while `ubuntu-26.04` is still in preview. This keeps the website workflows on a fixed Ubuntu runner label instead of switching to `ubuntu-latest`.

**Which issue(s) this PR fixes**:

None

**Special notes for your reviewer**:

Changed files:

- Updated all `runs-on: ubuntu-22.04` labels under `.github/workflows` to `runs-on: ubuntu-24.04`.
- No workflow logic, action version, script, or check command was changed.

Validation:

- `git grep -n "ubuntu-22.04" HEAD -- .github/workflows || true`
- `git diff --check upstream/main...HEAD`
- Parsed all `.github/workflows/*.yml` and `.github/workflows/*.yaml` with Python `yaml.safe_load`
- `git grep --cached -I $'\r'`: no CRLF line endings found

Fork push CI on `ranxi2001/website:chore/update-github-runner-ubuntu-24`, commit `24e7dd4515225a9462b47e04a7ca79285a586964`:

- `Typos Check`: passed

Note: `CRLF Check` only runs on `pull_request`; the equivalent local CRLF check passed.

This PR was prepared with AI assistance.
