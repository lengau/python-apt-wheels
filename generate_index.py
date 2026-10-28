#!/usr/bin/env python3
"""Generate PEP 503 compliant static simple repository index."""

import hashlib
import html
from pathlib import Path
import re
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


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_index.py <dist_dir> <output_dir> [base_url]")
        sys.exit(1)

    dist_dir = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    base_url = sys.argv[3].rstrip("/") if len(sys.argv) > 3 else ""

    simple_dir = out_dir / "simple"
    simple_dir.mkdir(parents=True, exist_ok=True)

    packages: dict[str, list[tuple[str, str, str]]] = {}

    for file_path in dist_dir.rglob("*.whl"):
        if not file_path.is_file():
            continue
        raw_name = parse_wheel_pkg_name(file_path.name)
        norm_name = normalize_name(raw_name)
        sha = sha256_file(file_path)

        if base_url:
            href = f"{base_url}/{file_path.name}#sha256={sha}"
        else:
            pkg_simple_dir = simple_dir / norm_name
            pkg_simple_dir.mkdir(parents=True, exist_ok=True)
            # Copy or hardlink wheel into pkg directory if relative
            target_wheel = pkg_simple_dir / file_path.name
            if not target_wheel.exists():
                target_wheel.write_bytes(file_path.read_bytes())
            href = f"{file_path.name}#sha256={sha}"

        packages.setdefault(norm_name, []).append((file_path.name, href, norm_name))

    # Generate each package index.html
    for norm_name, files in packages.items():
        pkg_dir = simple_dir / norm_name
        pkg_dir.mkdir(parents=True, exist_ok=True)
        links = "\n".join(
            f'    <a href="{html.escape(href)}">{html.escape(fname)}</a>'
            for fname, href, _ in sorted(files)
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

    # Generate root simple/index.html
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

    # Generate root index.html with instructions
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
