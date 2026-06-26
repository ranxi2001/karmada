#!/usr/bin/env python3
"""Audit Go module version resolution and package presence.

This is useful when a PR discussion depends on whether a dependency tag is a
canonical Go module version and whether expected API packages still exist.
"""

import argparse
import json
import os
import subprocess
import sys


def run(cmd):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return proc.returncode, proc.stdout, proc.stderr


def go_env():
    env = os.environ.copy()
    return env


def go_list_module(module, query):
    code, out, err = run(["go", "list", "-m", "-json", module + "@" + query])
    if code != 0:
        return None, err.strip()
    try:
        return json.loads(out), None
    except ValueError as exc:
        return None, "failed to parse go list JSON: %s" % exc


def go_versions(module):
    code, out, err = run(["go", "list", "-m", "-versions", module])
    if code != 0:
        return None, err.strip()
    return out.strip(), None


def package_exists(module_dir, package):
    if not module_dir:
        return None
    return os.path.isdir(os.path.join(module_dir, package))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", help="module path, e.g. k8s.io/api")
    parser.add_argument("queries", nargs="+", help="version queries, e.g. latest v0.5.0rc1")
    parser.add_argument(
        "--packages",
        nargs="*",
        default=[],
        help="module-relative package directories to check in each resolved version",
    )
    parser.add_argument("--show-versions", action="store_true", help="print go list -m -versions output")
    args = parser.parse_args()

    if args.show_versions:
        versions, err = go_versions(args.module)
        print("## versions")
        if err:
            print("ERROR:", err)
        else:
            print(versions)
        print()

    for query in args.queries:
        data, err = go_list_module(args.module, query)
        print("## %s@%s" % (args.module, query))
        if err:
            print("ERROR:", err)
            print()
            continue

        for key in ("Version", "Time", "GoVersion", "Dir", "GoMod", "Sum"):
            if key in data:
                print("- %s: %s" % (key, data[key]))
        origin = data.get("Origin") or {}
        if origin:
            print("- Origin: %s %s" % (origin.get("VCS", "-"), origin.get("Hash", "-")))

        if args.packages:
            print("- Packages:")
            for package in args.packages:
                exists = package_exists(data.get("Dir"), package)
                status = "present" if exists else "missing"
                print("  - %s: %s" % (package, status))
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
