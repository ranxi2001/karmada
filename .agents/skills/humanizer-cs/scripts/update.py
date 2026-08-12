#!/usr/bin/env python3
"""Check for and apply confirmed humanizer-cs releases."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile
import time
from typing import Any, Callable
import urllib.error
import urllib.parse
import urllib.request


REPOSITORY = "ranxi2001/humanizer-cs"
REPOSITORY_URL = f"https://github.com/{REPOSITORY}"
API_ROOT = f"https://api.github.com/repos/{REPOSITORY}"
ARCHIVE_ROOT = f"https://codeload.github.com/{REPOSITORY}/tar.gz"
USER_AGENT = "humanizer-cs-updater/1"
CACHE_TTL_SECONDS = 24 * 60 * 60
ERROR_CACHE_TTL_SECONDS = 60 * 60
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_ARCHIVE_EXPANDED_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 2048
MAX_RUNTIME_BYTES = 4 * 1024 * 1024
MAX_RUNTIME_FILES = 128
SEMVER_TAG = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
REQUIRED_RUNTIME_FILES = {
    "LICENSE",
    "SKILL.md",
    "VERSION",
    "agents/openai.yaml",
    "scripts/update.py",
}


class UpdateError(RuntimeError):
    """A user-facing updater failure."""


def skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_version(value: str) -> tuple[int, int, int]:
    normalized = value.strip()
    if not normalized.startswith("v"):
        normalized = f"v{normalized}"
    match = SEMVER_TAG.fullmatch(normalized)
    if not match:
        raise UpdateError(f"invalid semantic version: {value!r}")
    return tuple(int(part) for part in match.groups())


def canonical_tag(value: str) -> str:
    major, minor, patch = parse_version(value)
    return f"v{major}.{minor}.{patch}"


def version_text(value: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in value)


def confirmation_key(tag: str, release_id: int, commit: str) -> str:
    canonical = canonical_tag(tag)
    if release_id <= 0:
        raise UpdateError("release ID must be a positive integer")
    if not COMMIT_SHA.fullmatch(commit):
        raise UpdateError("expected commit must be a full lowercase commit SHA")
    return f"{canonical}:{release_id}:{commit}"


def read_current_version(target: Path) -> tuple[int, int, int]:
    version_file = target / "VERSION"
    try:
        raw = version_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise UpdateError(f"cannot read installed VERSION: {exc}") from exc
    return parse_version(raw)


def default_cache_path(target: Path) -> Path:
    cache_root = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache_root).expanduser() if cache_root else Path.home() / ".cache"
    identity = hashlib.sha256(str(target.resolve()).encode("utf-8")).hexdigest()[:16]
    return base / "humanizer-cs" / f"update-{identity}.json"


def _request_headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }


def request_bytes(
    url: str,
    *,
    limit: int,
    timeout: float = 10,
    opener: Callable[..., Any] | None = None,
) -> bytes:
    request = urllib.request.Request(url, headers=_request_headers())
    open_url = opener or urllib.request.urlopen
    try:
        with open_url(request, timeout=timeout) as response:
            raw_length = response.headers.get("Content-Length")
            if raw_length:
                try:
                    length = int(raw_length)
                except ValueError as exc:
                    raise UpdateError("server returned an invalid Content-Length") from exc
                if length > limit:
                    raise UpdateError(f"download exceeds the {limit}-byte limit")
            payload = response.read(limit + 1)
    except urllib.error.HTTPError as exc:
        raise UpdateError(f"GitHub request failed with HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UpdateError(f"GitHub request failed: {exc}") from exc
    if len(payload) > limit:
        raise UpdateError(f"download exceeds the {limit}-byte limit")
    return payload


def request_json(
    url: str,
    *,
    opener: Callable[..., Any] | None = None,
) -> Any:
    payload = request_bytes(url, limit=MAX_JSON_BYTES, opener=opener)
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError("GitHub returned invalid JSON") from exc


def stable_releases(*, opener: Callable[..., Any] | None = None) -> list[dict[str, Any]]:
    document = request_json(f"{API_ROOT}/releases?per_page=100", opener=opener)
    if not isinstance(document, list):
        raise UpdateError("GitHub releases response is not a list")
    releases: list[dict[str, Any]] = []
    for item in document:
        if not isinstance(item, dict) or item.get("draft") or item.get("prerelease"):
            continue
        tag = item.get("tag_name")
        release_id = item.get("id")
        release_url = item.get("html_url")
        if not isinstance(tag, str) or not SEMVER_TAG.fullmatch(tag):
            continue
        if not isinstance(release_id, int):
            continue
        if not isinstance(release_url, str) or not release_url.startswith(f"{REPOSITORY_URL}/releases/tag/"):
            continue
        releases.append(item)
    if not releases:
        raise UpdateError("GitHub returned no stable semantic-version releases")
    return releases


def latest_release(releases: list[dict[str, Any]]) -> dict[str, Any]:
    return max(releases, key=lambda item: parse_version(item["tag_name"]))


def exact_release(releases: list[dict[str, Any]], tag: str, release_id: int) -> dict[str, Any]:
    for release in releases:
        if release["tag_name"] == tag and release["id"] == release_id:
            return release
    raise UpdateError(f"stable release {tag} with id {release_id} was not found")


def resolve_tag_commit(tag: str, *, opener: Callable[..., Any] | None = None) -> str:
    quoted_tag = urllib.parse.quote(tag, safe="")
    document = request_json(f"{API_ROOT}/git/ref/tags/{quoted_tag}", opener=opener)
    if not isinstance(document, dict) or not isinstance(document.get("object"), dict):
        raise UpdateError(f"GitHub returned an invalid ref for {tag}")
    current = document["object"]
    for _ in range(5):
        object_type = current.get("type")
        sha = current.get("sha")
        if not isinstance(sha, str) or not COMMIT_SHA.fullmatch(sha):
            raise UpdateError(f"GitHub returned an invalid object SHA for {tag}")
        if object_type == "commit":
            return sha
        if object_type != "tag":
            raise UpdateError(f"tag {tag} resolves to unsupported object type {object_type!r}")
        tag_object = request_json(f"{API_ROOT}/git/tags/{sha}", opener=opener)
        if not isinstance(tag_object, dict) or not isinstance(tag_object.get("object"), dict):
            raise UpdateError(f"GitHub returned an invalid annotated tag object for {tag}")
        current = tag_object["object"]
    raise UpdateError(f"tag {tag} contains too many nested tag objects")


def _load_cache(path: Path) -> dict[str, Any] | None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        return None
    return document


def _write_cache(path: Path, current: str, checked_at: float, result: dict[str, Any]) -> None:
    document = {
        "schema_version": 1,
        "current_version": current,
        "checked_at": checked_at,
        "result": result,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".update-", suffix=".json", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=True, sort_keys=True)
            handle.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _cached_result(path: Path, current: str, now: float) -> dict[str, Any] | None:
    document = _load_cache(path)
    if not document or document.get("current_version") != current:
        return None
    checked_at = document.get("checked_at")
    result = document.get("result")
    if not isinstance(checked_at, (int, float)) or not isinstance(result, dict):
        return None
    ttl = ERROR_CACHE_TTL_SECONDS if result.get("status") == "unavailable" else CACHE_TTL_SECONDS
    if checked_at > now or now - checked_at >= ttl:
        return None
    cached = dict(result)
    cached["cached"] = True
    return cached


def check_for_update(
    *,
    target: Path | None = None,
    cache_path: Path | None = None,
    force: bool = False,
    opener: Callable[..., Any] | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    target = (target or skill_dir()).resolve()
    current_tuple = read_current_version(target)
    current = version_text(current_tuple)
    if os.environ.get("HUMANIZER_CS_NO_UPDATE_CHECK", "").casefold() in {"1", "true", "yes"}:
        return {"status": "disabled", "current_version": current, "cached": False}

    timestamp = time.time() if now is None else now
    selected_cache = cache_path or default_cache_path(target)
    if not force:
        cached = _cached_result(selected_cache, current, timestamp)
        if cached is not None:
            return cached

    try:
        release = latest_release(stable_releases(opener=opener))
        latest_tuple = parse_version(release["tag_name"])
        if latest_tuple <= current_tuple:
            result = {
                "status": "up_to_date",
                "current_version": current,
                "latest_version": version_text(latest_tuple),
                "cached": False,
            }
        else:
            commit = resolve_tag_commit(release["tag_name"], opener=opener)
            result = {
                "status": "update_available",
                "current_version": current,
                "latest_version": version_text(latest_tuple),
                "tag": release["tag_name"],
                "release_id": release["id"],
                "commit": commit,
                "confirmation_key": confirmation_key(release["tag_name"], release["id"], commit),
                "release_url": release["html_url"],
                "published_at": release.get("published_at"),
                "cached": False,
            }
    except UpdateError as exc:
        result = {
            "status": "unavailable",
            "current_version": current,
            "message": str(exc),
            "cached": False,
        }
    try:
        _write_cache(selected_cache, current, timestamp, result)
    except OSError:
        pass
    return result


def _ignored_local_path(relative: str) -> bool:
    path = PurePosixPath(relative)
    return path.name == ".DS_Store" or "__pycache__" in path.parts or path.suffix == ".pyc"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_runtime(target: Path, *, expected_version: str | None = None) -> dict[str, Any]:
    manifest_path = target / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UpdateError(
            "this installation predates managed updates; reinstall v0.4.6 or newer once before using upgrade"
        ) from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError(f"cannot read runtime manifest: {exc}") from exc

    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise UpdateError("runtime manifest has an unsupported schema")
    if manifest.get("name") != "humanizer-cs" or manifest.get("repository") != REPOSITORY:
        raise UpdateError("runtime manifest identifies an unexpected skill source")
    manifest_version = manifest.get("version")
    if not isinstance(manifest_version, str):
        raise UpdateError("runtime manifest has no version")
    canonical_manifest_version = version_text(parse_version(manifest_version))
    if expected_version and canonical_manifest_version != version_text(parse_version(expected_version)):
        raise UpdateError(
            f"runtime version {canonical_manifest_version} does not match expected {version_text(parse_version(expected_version))}"
        )
    installed_version = version_text(read_current_version(target))
    if installed_version != canonical_manifest_version:
        raise UpdateError("VERSION and runtime manifest disagree")

    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise UpdateError("runtime manifest has no managed files")
    expected_paths: set[str] = set()
    for relative, digest in files.items():
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise UpdateError("runtime manifest contains an invalid file entry")
        pure = PurePosixPath(relative)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or "\\" in relative
            or relative == "manifest.json"
        ):
            raise UpdateError(f"runtime manifest contains an unsafe path: {relative!r}")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise UpdateError(f"runtime manifest contains an invalid digest for {relative}")
        expected_paths.add(relative)

    actual_paths: set[str] = set()
    expected_directories = {
        parent.as_posix()
        for relative in expected_paths
        for parent in PurePosixPath(relative).parents
        if parent.as_posix() != "."
    }
    extra_directories: list[str] = []
    unsupported_entries: list[str] = []
    for path in target.rglob("*"):
        relative = path.relative_to(target).as_posix()
        if _ignored_local_path(relative):
            continue
        if path.is_symlink():
            raise UpdateError(f"runtime contains a symbolic link: {relative}")
        if path.is_dir():
            if relative not in expected_directories:
                extra_directories.append(relative)
        elif path.is_file() and relative != "manifest.json":
            actual_paths.add(relative)
        elif not path.is_file():
            unsupported_entries.append(relative)
    missing = sorted(expected_paths - actual_paths)
    extra = sorted(actual_paths - expected_paths)
    changed = sorted(
        relative
        for relative in expected_paths & actual_paths
        if _sha256(target / relative) != files[relative]
    )
    if missing or extra or extra_directories or unsupported_entries or changed:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if extra:
            details.append(f"extra: {', '.join(extra)}")
        if extra_directories:
            details.append(f"extra directories: {', '.join(sorted(extra_directories))}")
        if unsupported_entries:
            details.append(f"unsupported entries: {', '.join(sorted(unsupported_entries))}")
        if changed:
            details.append(f"changed: {', '.join(changed)}")
        raise UpdateError("local skill files differ from the installed manifest (" + "; ".join(details) + ")")
    if not REQUIRED_RUNTIME_FILES <= expected_paths:
        missing_required = sorted(REQUIRED_RUNTIME_FILES - expected_paths)
        raise UpdateError(f"runtime manifest omits required files: {', '.join(missing_required)}")
    return manifest


def download_archive(commit: str, *, opener: Callable[..., Any] | None = None) -> bytes:
    if not COMMIT_SHA.fullmatch(commit):
        raise UpdateError("refusing to download an invalid commit SHA")
    return request_bytes(
        f"{ARCHIVE_ROOT}/{commit}",
        limit=MAX_ARCHIVE_BYTES,
        timeout=20,
        opener=opener,
    )


def stage_runtime(archive: bytes, parent: Path, *, expected_version: str) -> Path:
    stage = Path(tempfile.mkdtemp(prefix=".humanizer-cs-stage-", dir=parent))
    seen: set[str] = set()
    archive_members = 0
    archive_expanded_size = 0
    runtime_files = 0
    total_size = 0
    try:
        try:
            bundle = tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz")
        except (tarfile.TarError, OSError) as exc:
            raise UpdateError("downloaded release archive is not a valid gzip tar file") from exc
        with bundle:
            for member in bundle:
                archive_members += 1
                if archive_members > MAX_ARCHIVE_MEMBERS:
                    raise UpdateError("release archive contains too many entries")
                archive_expanded_size += member.size
                if archive_expanded_size > MAX_ARCHIVE_EXPANDED_BYTES:
                    raise UpdateError("release archive exceeds the expanded-size limit")
                if "\\" in member.name:
                    raise UpdateError(f"release archive contains an unsafe path: {member.name!r}")
                archive_path = PurePosixPath(member.name)
                if archive_path.is_absolute() or ".." in archive_path.parts:
                    raise UpdateError(f"release archive contains an unsafe path: {member.name!r}")
                parts = archive_path.parts
                if len(parts) < 3 or parts[1:3] != ("skills", "humanizer-cs"):
                    continue
                relative_parts = parts[3:]
                if not relative_parts:
                    if not member.isdir():
                        raise UpdateError("release archive has an invalid skill root")
                    continue
                relative = PurePosixPath(*relative_parts).as_posix()
                if relative in seen:
                    raise UpdateError(f"release archive contains duplicate path: {relative}")
                seen.add(relative)
                destination = stage.joinpath(*relative_parts)
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    raise UpdateError(f"release archive contains a non-regular runtime file: {relative}")
                runtime_files += 1
                if runtime_files > MAX_RUNTIME_FILES:
                    raise UpdateError("release archive contains too many runtime files")
                total_size += member.size
                if total_size > MAX_RUNTIME_BYTES:
                    raise UpdateError("release runtime exceeds the extracted-size limit")
                source = bundle.extractfile(member)
                if source is None:
                    raise UpdateError(f"cannot read release archive member: {relative}")
                payload = source.read(member.size + 1)
                if len(payload) != member.size:
                    raise UpdateError(f"release archive member has an invalid size: {relative}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as handle:
                    handle.write(payload)
        validate_runtime(stage, expected_version=expected_version)
        return stage
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _path_contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def apply_upgrade(
    *,
    version: str,
    release_id: int,
    commit: str,
    confirmation: str,
    target: Path | None = None,
    cache_path: Path | None = None,
    opener: Callable[..., Any] | None = None,
    replace: Callable[[Path, Path], Any] | None = None,
) -> dict[str, Any]:
    requested_tag = canonical_tag(version)
    expected_confirmation = confirmation_key(requested_tag, release_id, commit)
    if confirmation != expected_confirmation:
        raise UpdateError("confirmation key does not match the checked release")

    unresolved_target = target or skill_dir()
    if unresolved_target.is_symlink():
        raise UpdateError("refusing to replace a symbolic-link installation")
    target = unresolved_target.resolve()
    if _path_contains(target, Path.cwd().resolve()):
        raise UpdateError("run the updater from outside the installed skill directory")
    current = read_current_version(target)
    requested = parse_version(requested_tag)
    if requested <= current:
        raise UpdateError(
            f"refusing non-upgrade transition {version_text(current)} -> {version_text(requested)}"
        )
    validate_runtime(target, expected_version=version_text(current))

    releases = stable_releases(opener=opener)
    release = exact_release(releases, requested_tag, release_id)
    resolved_commit = resolve_tag_commit(requested_tag, opener=opener)
    if resolved_commit != commit:
        raise UpdateError(
            f"release {requested_tag} changed after confirmation: expected {commit}, found {resolved_commit}"
        )
    archive = download_archive(commit, opener=opener)
    stage = stage_runtime(archive, target.parent, expected_version=version_text(requested))

    timestamp = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    backup = target.parent / f".{target.name}-backup-{version_text(current)}-{timestamp}"
    counter = 1
    while backup.exists():
        backup = target.parent / f".{target.name}-backup-{version_text(current)}-{timestamp}-{counter}"
        counter += 1
    replace_path = replace or os.replace
    try:
        validate_runtime(target, expected_version=version_text(current))
        try:
            replace_path(target, backup)
            replace_path(stage, target)
        except BaseException as install_error:
            if backup.exists() and target.exists() and not stage.exists():
                try:
                    validate_runtime(target, expected_version=version_text(requested))
                except UpdateError as validation_error:
                    raise UpdateError(
                        f"upgrade was interrupted after replacement; inspect the active installation and backup {backup}: {validation_error}"
                    ) from install_error
                raise UpdateError(
                    f"upgrade was interrupted after replacement completed; version {version_text(requested)} is active and the backup is {backup}"
                ) from install_error
            if not backup.exists():
                raise UpdateError(f"cannot create a backup of the current installation: {install_error}") from install_error
            try:
                replace_path(backup, target)
            except BaseException as rollback_error:
                raise UpdateError(
                    f"upgrade and rollback both failed; recover the previous installation from {backup}"
                ) from rollback_error
            raise UpdateError(f"upgrade failed and the previous installation was restored: {install_error}") from install_error
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)

    selected_cache = cache_path or default_cache_path(target)
    try:
        selected_cache.unlink(missing_ok=True)
    except OSError:
        pass
    return {
        "status": "upgraded",
        "previous_version": version_text(current),
        "current_version": version_text(requested),
        "tag": requested_tag,
        "commit": commit,
        "release_url": release["html_url"],
        "backup": str(backup),
        "restart_required": True,
    }


def _render_check(result: dict[str, Any]) -> str:
    status = result["status"]
    if status == "update_available":
        return (
            f"humanizer-cs {result['current_version']} -> {result['latest_version']} is available\n"
            f"source: {REPOSITORY}\n"
            f"tag: {result['tag']}\n"
            f"commit: {result['commit']}\n"
            f"confirmation key: {result['confirmation_key']}\n"
            f"release: {result['release_url']}\n"
            "No files were changed. Confirm this exact release before running upgrade."
        )
    if status == "up_to_date":
        return f"humanizer-cs {result['current_version']} is up to date"
    if status == "disabled":
        return "humanizer-cs update checks are disabled"
    return f"humanizer-cs update check unavailable: {result.get('message', 'unknown error')}"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="check stable GitHub releases")
    check_parser.add_argument("--force", action="store_true", help="ignore the local check cache")
    check_parser.add_argument("--json", action="store_true", help="print structured JSON")

    upgrade_parser = subparsers.add_parser("upgrade", help="apply one explicitly confirmed release")
    upgrade_parser.add_argument("--version", required=True, help="exact release tag, such as v0.4.7")
    upgrade_parser.add_argument("--release-id", required=True, type=int, help="GitHub release id from check")
    upgrade_parser.add_argument("--commit", required=True, help="full commit SHA from check")
    upgrade_parser.add_argument("--confirm", required=True, help="exact confirmation key from check")
    upgrade_parser.add_argument("--json", action="store_true", help="print structured JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command == "check":
            result = check_for_update(force=args.force)
            print(json.dumps(result, sort_keys=True) if args.json else _render_check(result))
            return 0
        result = apply_upgrade(
            version=args.version,
            release_id=args.release_id,
            commit=args.commit,
            confirmation=args.confirm,
        )
        if args.json:
            print(json.dumps(result, sort_keys=True))
        else:
            print(
                f"Upgraded humanizer-cs {result['previous_version']} -> {result['current_version']}.\n"
                f"Backup: {result['backup']}\nRestart the agent client to load the new skill."
            )
        return 0
    except UpdateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
