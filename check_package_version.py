#!/usr/bin/env python3
"""Check Launchpad for latest python-apt version in series and compare against existing releases."""

import argparse
import json
import os
import subprocess
import sys
import urllib.request


def get_pep440_version(deb_ver: str) -> str:
    v = deb_ver.strip()
    v = v.replace("~alpha", ".a")
    v = v.replace("~beta", ".b")
    v = v.replace("~rc", ".rc")
    v = v.replace("~exp", ".dev")
    v = v.replace("ubuntu", "+ubuntu")
    v = v.replace("tanglu", "+tanglu")
    v = v.split("build")[0]
    try:
        from packaging.version import Version
        return str(Version(v))
    except Exception:
        return v


def is_workflow_modified(event: str, base_ref: str = "") -> bool:
    try:
        commands = []
        if event == "pull_request" and base_ref:
            commands.append(["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"])
            commands.append(["git", "diff", "--name-only", f"{base_ref}...HEAD"])
        elif event == "push":
            commands.append(["git", "diff", "--name-only", "HEAD~1", "HEAD"])
        commands.append(["git", "diff", "--name-only", "HEAD~1"])

        for cmd in commands:
            try:
                res = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                for line in res.splitlines():
                    if line.strip().startswith(".github/workflows/"):
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def main():
    parser = argparse.ArgumentParser(description="Check Launchpad and GitHub releases for python-apt wheels.")
    parser.add_argument("series", help="Ubuntu series")
    parser.add_argument("arch", help="Target architecture")
    parser.add_argument("--event", default="", help="GitHub workflow trigger event name")
    parser.add_argument("--base-ref", default="", help="Base branch ref for pull_request")
    parser.add_argument("--target-arch", default=None, help="Target architecture for workflow_dispatch")
    parser.add_argument("--target-series", default=None, help="Target series for workflow_dispatch")
    parser.add_argument("--force", action="store_true", help="Force rebuild regardless of existing releases")

    args = parser.parse_args()

    series = args.series
    arch = args.arch
    arch_to_wheel = {
        "amd64": "x86_64",
        "arm64": "aarch64",
        "armhf": "armv7l",
        "armv7l": "armv7l",
        "s390x": "s390x",
        "ppc64el": "ppc64le",
        "ppc64le": "ppc64le",
        "riscv64": "riscv64",
        "risc-v": "riscv64",
    }
    wheel_arch = arch_to_wheel.get(arch, arch)

    if is_workflow_modified(args.event, args.base_ref):
        print(f"Workflow file modification detected. Proceeding with build for {series} ({arch}).")
        set_output(skip=False)
        return

    if args.event == "workflow_dispatch":
        target_arch = args.target_arch or "all"
        target_series = args.target_series or "all"
        arch_matches = (target_arch == "all") or (target_arch == arch)
        series_matches = (target_series == "all") or (target_series == series)

        if not (arch_matches and series_matches):
            print(f"Skipping {series} ({arch}): not targeted by workflow_dispatch (target arch: {target_arch}, target series: {target_series}).")
            set_output(skip=True)
            return

        print(f"Force-rebuild requested via workflow_dispatch for {series} ({arch}). Proceeding with build.")
        set_output(skip=False)
        return

    if args.force:
        print(f"Force rebuild explicitly requested for {series} ({arch}). Proceeding with build.")
        set_output(skip=False)
        return

    url = f"https://api.launchpad.net/1.0/ubuntu/+archive/primary?ws.op=getPublishedSources&source_name=python-apt&exact_match=true&distro_series=https://api.launchpad.net/1.0/ubuntu/{series}"
    req = urllib.request.Request(url, headers={"User-Agent": "python-apt-wheels-ci"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Warning: Failed to fetch from Launchpad ({e}). Proceeding with build.")
        set_output(skip=False)
        return

    entries = [
        e for e in data.get("entries", [])
        if e.get("status") in ("Published", "Obsolete")
    ]

    if not entries:
        print(f"No published source found on Launchpad for series {series}. Building.")
        set_output(skip=False)
        return

    entries.sort(key=lambda e: e.get("date_published", ""))
    deb_version = entries[-1]["source_package_version"]
    wheel_ver = get_pep440_version(deb_version)
    print(f"Series: {series}, Latest version: {deb_version} (wheel: {wheel_ver}), Arch: {wheel_arch}")

    # Check existing GitHub release assets using gh
    try:
        res = subprocess.check_output(
            ["gh", "release", "list", "--json", "tagName"],
            text=True
        )
        releases = json.loads(res)
    except Exception as e:
        print(f"Warning: Failed to list releases ({e}). Building.")
        set_output(skip=False)
        return

    for r in releases[:10]:
        tag = r["tagName"]
        try:
            assets_raw = subprocess.check_output(
                ["gh", "release", "view", tag, "--json", "assets"],
                text=True
            )
            assets = json.loads(assets_raw).get("assets", [])
        except Exception:
            continue

        matches = [
            a["name"] for a in assets
            if a["name"].startswith(f"python_apt-{wheel_ver}-") and a["name"].endswith(f"_{wheel_arch}.whl")
        ]
        if matches:
            print(f"Matching wheels for {wheel_ver} ({wheel_arch}) already exist in release '{tag}'. Skipping build.")
            set_output(skip=True)
            return

    print(f"No existing wheels found for {wheel_ver} ({wheel_arch}). Proceeding with build.")
    set_output(skip=False)


def set_output(skip: bool):
    github_output = os.environ.get("GITHUB_OUTPUT")
    val = "true" if skip else "false"
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"skip={val}\n")
    print(f"OUTPUT: skip={val}")


if __name__ == "__main__":
    main()
