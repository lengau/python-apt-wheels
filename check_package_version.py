#!/usr/bin/env python3
"""Check Launchpad for latest python-apt version in series and compare against existing releases."""

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


def main():
    if len(sys.argv) < 3:
        print("Usage: check_package_version.py <series> <arch>")
        sys.exit(1)

    series = sys.argv[1]
    arch = sys.argv[2]  # amd64 or arm64
    wheel_arch = "x86_64" if arch == "amd64" else "aarch64"

    url = "https://api.launchpad.net/1.0/ubuntu/+archive/primary?ws.op=getPublishedSources&source_name=python-apt&exact_match=true&status=Published"
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
        if e.get("distro_series_link", "").rstrip("/").endswith(f"/{series}")
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
