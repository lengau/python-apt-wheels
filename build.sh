#!/bin/bash
set -e

cd /tmp

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get source python-apt
cd python-apt-*

export GLIBC_VERSION="$(ldd --version | grep GLIBC | cut -d' ' -f4 | cut -d- -f1 | tr . _)"
export DEBVER="$(apt-cache show python3-apt|grep Version | head -n 1|cut -d' ' -f2)"

export MAKEOPTS="-j$(nproc)"

for UV_PYTHON in 3.10 3.11 3.12 3.13 3.14 3.14t; do
    export UV_PYTHON
    /root/.local/bin/uv venv
    /root/.local/bin/uv pip install setuptools
    source .venv/bin/activate
    python3 setup.py bdist_wheel --dist-dir /github/workspace --plat-name "manylinux_${GLIBC_VERSION}_$(uname -m)"
done
