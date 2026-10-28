# python-apt Wheels

Pre-built binary wheels for `python-apt` across Ubuntu LTS and interim releases on `x86_64` (amd64), `aarch64` (arm64), `armv7l` (armhf), `s390x`, `ppc64le` (ppc64el), and `riscv64`.

Hosted as a static PEP 503 simple repository via GitHub Pages:
**`https://lengau.github.io/python-apt-wheels/simple/`**

---

## Supported Releases & Series

| Ubuntu Series | Version | Default CPython Versions | Architectures |
|---------------|---------|--------------------------|---------------|
| **Bionic** | 18.04 | 3.6, 3.8, 3.9 | amd64, arm64, armhf, s390x, ppc64el |
| **Focal** | 20.04 | 3.8 – 3.14, 3.14t | amd64, arm64, armhf, s390x, ppc64el, riscv64 |
| **Jammy** | 22.04 | 3.8 – 3.14, 3.14t | amd64, arm64, armhf, s390x, ppc64el, riscv64 |
| **Noble** | 24.04 | 3.8 – 3.14, 3.14t | amd64, arm64, armhf, s390x, ppc64el, riscv64 |
| **Resolute** | 26.04 | 3.8 – 3.14, 3.14t | amd64, arm64, armhf, s390x, ppc64el, riscv64 |
| **Stonking** | 26.10 | 3.8 – 3.14, 3.14t | amd64, arm64, armhf, s390x, ppc64el, riscv64 |

---

## Using with `uv`

### 1. `pyproject.toml` Configuration

To use these wheels in a project managed by `uv`, declare the index in `pyproject.toml`:

```toml
[[tool.uv.index]]
name = "python-apt-wheels"
url = "https://lengau.github.io/python-apt-wheels/simple/"
explicit = true

[tool.uv.sources]
python-apt = { index = "python-apt-wheels" }
```

### 2. Targeting Specific Ubuntu Series via Dependency Groups

Because `python-apt` links dynamically against `libapt-pkg` of the underlying host release, specify matching version constraints for each series:

```toml
[dependency-groups]
dev-focal = [
  { name = "python-apt", marker = "sys_platform == 'linux'", specifier = "~=2.0.0", index = "python-apt-wheels" },
]
dev-jammy = [
  { name = "python-apt", marker = "sys_platform == 'linux'", specifier = "~=2.4.0", index = "python-apt-wheels" },
]
dev-noble = [
  { name = "python-apt", marker = "sys_platform == 'linux'", specifier = "~=2.7.0", index = "python-apt-wheels" },
]
dev-resolute = [
  { name = "python-apt", marker = "sys_platform == 'linux'", specifier = "~=3.1.0", index = "python-apt-wheels" },
]
dev-stonking = [
  { name = "python-apt", marker = "sys_platform == 'linux'", specifier = "~=3.1.0", index = "python-apt-wheels" },
]
```

To prevent version conflicts when resolving a shared lockfile, declare mutually exclusive dependency groups in `[tool.uv]`:

```toml
[tool.uv]
conflicts = [
  [
    { group = "dev-focal" },
    { group = "dev-jammy" },
    { group = "dev-noble" },
    { group = "dev-resolute" },
    { group = "dev-stonking" },
  ],
]
```

Then install the appropriate group in your virtual environment:

```bash
uv sync --group dev-noble
```

---

## Ad-hoc Installation

### With `uv`

```bash
uv pip install --extra-index-url https://lengau.github.io/python-apt-wheels/simple/ python-apt
```

### With `pip`

```bash
pip install --extra-index-url https://lengau.github.io/python-apt-wheels/simple/ python-apt
```

---

## Local Development & Building

Build images and wheels locally using `podman` (or set `CONTAINER_ENGINE=docker`):

```bash
# Build image for a series
make build-image SERIES=noble

# Build wheels inside the container
make wheel SERIES=noble
```
