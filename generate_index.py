#!/usr/bin/env python3
"""Generate PEP 503 compliant static simple repository index.

Discovers all wheels from local artifacts as well as all GitHub Releases
across repository history.
"""

import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys


def normalize_name(name: str) -> str:
    """PEP 503 package name normalization."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_wheel_pkg_name(filename: str) -> str:
    """Extract package name from wheel filename."""
    return filename.split("-")[0]


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_releases_wheels(repo: str) -> dict[str, tuple[str, str]]:
    """Query GitHub releases to collect wheels and their download URLs."""
    wheels: dict[str, tuple[str, str]] = {}
    try:
        cmd = ["gh", "release", "list", "--limit", "100", "--json", "tagName"]
        if repo:
            cmd.extend(["--repo", repo])
        res = subprocess.check_output(cmd, text=True)
        releases = json.loads(res)
    except Exception as e:
        print(f"Warning: Could not list releases via gh: {e}")
        return wheels

    for r in releases:
        tag = r["tagName"]
        try:
            view_cmd = ["gh", "release", "view", tag, "--json", "assets"]
            if repo:
                view_cmd.extend(["--repo", repo])
            raw = subprocess.check_output(view_cmd, text=True)
            assets = json.loads(raw).get("assets", [])
        except Exception:
            continue

        for a in assets:
            name = a.get("name", "")
            if not name.endswith(".whl"):
                continue
            url = a.get("url")
            digest = a.get("digest") or ""
            sha = digest.replace("sha256:", "") if digest.startswith("sha256:") else ""
            if name not in wheels and url:
                wheels[name] = (url, sha)

    return wheels


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_index.py <dist_dir> <output_dir> [repo] [current_tag]")
        sys.exit(1)

    dist_dir = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    repo = sys.argv[3] if len(sys.argv) > 3 else ""
    current_tag = sys.argv[4] if len(sys.argv) > 4 else ""

    simple_dir = out_dir / "simple"
    simple_dir.mkdir(parents=True, exist_ok=True)

    # Map package_name -> dict(filename -> href)
    packages: dict[str, dict[str, str]] = {}

    # 1. Collect all wheels from GitHub Releases across history
    remote_wheels = get_releases_wheels(repo)
    print(f"Discovered {len(remote_wheels)} wheel assets from GitHub Releases.")
    for fname, (url, sha) in remote_wheels.items():
        norm_name = normalize_name(parse_wheel_pkg_name(fname))
        href = f"{url}#sha256={sha}" if sha else url
        packages.setdefault(norm_name, {})[fname] = href

    # 2. Add local newly built wheels (with exact computed sha256)
    if dist_dir.exists():
        for file_path in dist_dir.rglob("*.whl"):
            if not file_path.is_file():
                continue
            norm_name = normalize_name(parse_wheel_pkg_name(file_path.name))
            sha = sha256_file(file_path)
            if repo and current_tag:
                url = f"https://github.com/{repo}/releases/download/{current_tag}/{file_path.name}"
                href = f"{url}#sha256={sha}"
            else:
                pkg_simple_dir = simple_dir / norm_name
                pkg_simple_dir.mkdir(parents=True, exist_ok=True)
                target_wheel = pkg_simple_dir / file_path.name
                if not target_wheel.exists():
                    target_wheel.write_bytes(file_path.read_bytes())
                href = f"{file_path.name}#sha256={sha}"

            packages.setdefault(norm_name, {})[file_path.name] = href

    # 3. Generate each package index.html
    for norm_name, files_map in packages.items():
        pkg_dir = simple_dir / norm_name
        pkg_dir.mkdir(parents=True, exist_ok=True)
        links = "\n".join(
            f'    <a href="{html.escape(href)}">{html.escape(fname)}</a>'
            for fname, href in sorted(files_map.items())
        )
        pkg_html = f"""<!DOCTYPE html>
<html>
  <head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Links for {html.escape(norm_name)}</title>
  </head>
  <body>
    <h1>Links for {html.escape(norm_name)}</h1>
{links}
  </body>
</html>
"""
        (pkg_dir / "index.html").write_text(pkg_html, encoding="utf-8")

    # 4. Generate root simple/index.html
    root_links = "\n".join(
        f'    <a href="{html.escape(pkg)}/">{html.escape(pkg)}</a>'
        for pkg in sorted(packages.keys())
    )
    simple_index = f"""<!DOCTYPE html>
<html>
  <head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Simple Index</title>
  </head>
  <body>
    <h1>Simple Index</h1>
{root_links}
  </body>
</html>
"""
    (simple_dir / "index.html").write_text(simple_index, encoding="utf-8")

    # 5. Generate root landing index.html
    index_html = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>python-apt Wheels Repository</title>
  </head>
  <body>
    <h1>python-apt Wheels Repository</h1>
    <p>PEP 503 Simple Index available at <a href="simple/">/simple/</a>.</p>
    <h2>Usage with uv</h2>
    <pre><code>uv pip install --extra-index-url &lt;this-url&gt;simple/ python-apt</code></pre>
    <h2>Usage with pip</h2>
    <pre><code>pip install --extra-index-url &lt;this-url&gt;simple/ python-apt</code></pre>
  </body>
</html>
"""
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")


if __name__ == "__main__":
    main()
