#!/usr/bin/env python3
"""Check if published container image exists in GHCR and whether it is under the max age limit."""

import argparse
import base64
from datetime import datetime, timedelta, timezone
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request


def parse_iso_datetime(dt_str: str) -> datetime | None:
    try:
        cleaned = re.sub(r"(\.\d{6})\d+", r"\1", dt_str).replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def get_image_created_at(image: str) -> datetime | None:
    # 1. Try skopeo inspect
    try:
        cmd = ["skopeo", "inspect", f"docker://{image}"]
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        actor = os.environ.get("GITHUB_ACTOR")
        if token and actor:
            cmd.extend(["--creds", f"{actor}:{token}"])
        res = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        data = json.loads(res)
        created_str = data.get("Created")
        if created_str:
            dt = parse_iso_datetime(created_str)
            if dt:
                return dt
    except Exception:
        pass

    # 2. HTTP Registry fallback
    try:
        parts = image.removeprefix("ghcr.io/").split(":")
        repo_name = parts[0]
        tag = parts[1] if len(parts) > 1 else "latest"

        token_url = f"https://ghcr.io/token?service=ghcr.io&scope=repository:{repo_name}:pull"
        req = urllib.request.Request(token_url)
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        actor = os.environ.get("GITHUB_ACTOR", "actor")
        if token:
            auth_str = base64.b64encode(f"{actor}:{token}".encode()).decode()
            req.add_header("Authorization", f"Basic {auth_str}")
        with urllib.request.urlopen(req) as resp:
            registry_token = json.loads(resp.read().decode())["token"]

        manifest_url = f"https://ghcr.io/v2/{repo_name}/manifests/{tag}"
        req = urllib.request.Request(
            manifest_url,
            headers={
                "Authorization": f"Bearer {registry_token}",
                "Accept": "application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json",
            },
        )
        with urllib.request.urlopen(req) as resp:
            manifest = json.loads(resp.read().decode())

        if "annotations" in manifest and "org.opencontainers.image.created" in manifest["annotations"]:
            dt = parse_iso_datetime(manifest["annotations"]["org.opencontainers.image.created"])
            if dt:
                return dt

        if "config" in manifest and "digest" in manifest["config"]:
            blob_digest = manifest["config"]["digest"]
            blob_url = f"https://ghcr.io/v2/{repo_name}/blobs/{blob_digest}"
            req = urllib.request.Request(blob_url, headers={"Authorization": f"Bearer {registry_token}"})
            with urllib.request.urlopen(req) as resp:
                config = json.loads(resp.read().decode())
                created_str = config.get("created")
                if created_str:
                    dt = parse_iso_datetime(created_str)
                    if dt:
                        return dt
    except Exception:
        pass

    return None


def set_output(skip: bool):
    github_output = os.environ.get("GITHUB_OUTPUT")
    val = "true" if skip else "false"
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"skip={val}\n")
    print(f"OUTPUT: skip={val}")


def main():
    parser = argparse.ArgumentParser(description="Check container image age in GHCR.")
    parser.add_argument("image", help="Container image tag to inspect (e.g. ghcr.io/owner/repo:tag)")
    parser.add_argument("--series", default="", help="Ubuntu series")
    parser.add_argument("--arch", default="", help="Target architecture")
    parser.add_argument("--max-age-days", type=float, default=6.0, help="Maximum image age in days before rebuilding")
    parser.add_argument("--event", default="", help="GitHub workflow trigger event name")
    parser.add_argument("--target-arch", default=None, help="Target architecture for workflow_dispatch")
    parser.add_argument("--target-series", default=None, help="Target series for workflow_dispatch")
    parser.add_argument("--force", action="store_true", help="Force rebuild regardless of image age")

    args = parser.parse_args()

    series = args.series
    arch = args.arch

    if args.event == "workflow_dispatch":
        target_arch = args.target_arch or "all"
        target_series = args.target_series or "all"
        arch_matches = (target_arch == "all") or (target_arch == arch)
        series_matches = (target_series == "all") or (target_series == series)

        if not (arch_matches and series_matches):
            print(
                f"Skipping image build for {series} ({arch}): not targeted by workflow_dispatch "
                f"(target arch: {target_arch}, target series: {target_series})."
            )
            set_output(skip=True)
            return

        print(f"Force-rebuild requested via workflow_dispatch for {series} ({arch}). Proceeding with image build.")
        set_output(skip=False)
        return

    if args.force:
        print(f"Force rebuild explicitly requested for {args.image}. Proceeding with image build.")
        set_output(skip=False)
        return

    created_dt = get_image_created_at(args.image)
    if not created_dt:
        print(f"Image '{args.image}' not found in registry or creation time unavailable. Proceeding with image build.")
        set_output(skip=False)
        return

    now = datetime.now(timezone.utc)
    age = now - created_dt
    age_days = age.total_seconds() / 86400.0
    print(f"Image '{args.image}' was created at {created_dt.isoformat()} ({age_days:.2f} days old).")

    if age < timedelta(days=args.max_age_days):
        print(f"Image is under {args.max_age_days} days old. Skipping image build.")
        set_output(skip=True)
    else:
        print(f"Image is older than {args.max_age_days} days. Proceeding with image build.")
        set_output(skip=False)


if __name__ == "__main__":
    main()
